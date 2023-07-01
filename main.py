import os
from enum import Enum
from pprint import pprint
from typing import List

import aiohttp

import anyio
import bs4
import pymorphy2
from aiohttp import ClientResponseError
from anyio import create_task_group

from text_tools import split_by_words, calculate_jaundice_rate


class JaundiceRater:

    def __init__(self, urls: List[str]):
        self.urls = urls
        self.results = []
        self.charged_words = []
        self.get_charged_words()

    async def rate(self):
        async with create_task_group() as tg:
            for url in self.urls:
                tg.start_soon(self.rate_article, url)

    async def get_article_text(self, url: str):
        async with aiohttp.ClientSession() as self.session:
            html = await self.fetch(url)
        soup = bs4.BeautifulSoup(html, 'lxml')
        paragraphs = soup.find('div', class_='article__body').find_all('div', class_='article__text')
        text = '\n'.join([p.text for p in paragraphs])
        return text

    def get_charged_words(self, dict_path: str = 'charged_dict'):
        for file in os.listdir(dict_path):
            with open(os.path.join(dict_path, file), encoding='utf8') as f:
                self.charged_words.extend([
                    line.strip() for line in f.readlines()
                ])

    async def fetch(self, url):
        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.text()

    async def rate_article(self, url: str):
        result = {
            'url': url
        }
        try:
            text = await self.get_article_text(url)
        except ClientResponseError:
            result.update({
                'Статус': ProcessingStatus.FETCH_ERROR,
                'rate': None,
                'words_count': None
            })
        else:
            words = split_by_words(pymorphy2.MorphAnalyzer(), text)
            rate = calculate_jaundice_rate(words, self.charged_words)
            result.update({
                'Статус': ProcessingStatus.OK,
                'rate': rate,
                'words_count': len(words)
            })
        self.results.append(result)


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'

    def __str__(self):
        return str(self.value)


def main():
    urls = [
        'https://inosmi.ru/economic/20190629/245384784.html',
        'https://inosmi.ru/politic/20190629/245379332.html',
        'https://inosmi.ru/20200119/246647767.html',
        'https://inosmi.ru/20230701/fobii-264001674.html',
        'https://inosmi.ru/20230701/britaniya-2640104.html'
    ]
    rater = JaundiceRater(urls)
    anyio.run(rater.rate)
    pprint(rater.results)


if __name__ == '__main__':
    main()
