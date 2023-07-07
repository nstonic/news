import asyncio
import os
from enum import Enum
from typing import List

import aiofiles
import aiohttp

import anyio
import pymorphy2
from aiohttp import ClientResponseError, InvalidURL, ClientConnectorError
from async_timeout import timeout

from adapters import ArticleNotFound
from adapters.inosmi_ru import sanitize
from text_tools import split_by_words, calculate_jaundice_rate


class JaundiceRater:
    morph = None
    charged_words = list()

    def __init__(self, dict_path: str = 'charged_dict'):
        self._results = list()
        if not self.charged_words:
            self.collect_charged_words(dict_path)
        if not self.morph:
            self.__class__.morph = pymorphy2.MorphAnalyzer()

    @classmethod
    def collect_charged_words(cls, dict_path: str):
        for file in os.listdir(dict_path):
            with open(os.path.join(dict_path, file), encoding='utf8') as f:
                cls.charged_words.extend([
                    line.strip() for line in f.readlines()
                ])

    @property
    def results(self):
        return self._results

    async def rate(self, urls: List[str]):
        async with anyio.create_task_group() as tg:
            for url in urls:
                tg.start_soon(self.process_article, url)

    def clean_results(self):
        self._results = list()

    async def get_article_text(self, url: str):
        async with aiohttp.ClientSession() as self.session:
            html = await self.fetch(url)
        return sanitize(html)

    async def fetch(self, url):
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.text()

    async def process_article(self, url: str):
        result = {
            'url': url,
            'score': None,
            'words': None
        }
        try:
            async with timeout(3):
                text = await self.get_article_text(url)
            async with timeout(3):
                words = await split_by_words(self.morph, text)
        except (ClientResponseError, ClientConnectorError, InvalidURL):
            result.update({
                'status': ProcessingStatus.FETCH_ERROR.value
            })
        except asyncio.exceptions.TimeoutError:
            result.update({
                'status': ProcessingStatus.TIMEOUT.value
            })
        except ArticleNotFound:
            result.update({
                'status': ProcessingStatus.PARSING_ERROR.value
            })
        else:
            rate = calculate_jaundice_rate(words, self.charged_words)
            result.update({
                'status': ProcessingStatus.OK.value,
                'score': rate,
                'words': len(words)
            })
        self._results.append(result)


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


async def get_long_article(*args):
    async with aiofiles.open('long.txt', mode='r', encoding='utf8') as f:
        return await f.read()


def test_process_article():
    rater = JaundiceRater()
    anyio.run(rater.rate, ['https://inosmi.ru/economic/20190629/245384784.html'])
    assert rater.results[0]['status'] == ProcessingStatus.OK.value

    rater.clean_results()
    anyio.run(rater.rate, ['https://inosmiI.ru/20190629/2453484784.html'])
    assert rater.results[0]['status'] == ProcessingStatus.FETCH_ERROR.value

    rater.clean_results()
    anyio.run(rater.rate, ['https://russian.rt.com/world/news/1170140-kitai-vizit-borrel'])
    assert rater.results[0]['status'] == ProcessingStatus.PARSING_ERROR.value

    rater.clean_results()
    rater.get_article_text = get_long_article
    anyio.run(rater.rate, ['https://ya.ru'])
    assert rater.results[0]['status'] == ProcessingStatus.TIMEOUT.value


if __name__ == '__main__':
    test_process_article()
