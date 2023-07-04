import asyncio
import os
from enum import Enum
from typing import List

import aiohttp

import anyio
import pymorphy2
from aiohttp import ClientResponseError
from async_timeout import timeout

from adapters import ArticleNotFound
from adapters.inosmi_ru import sanitize
from text_tools import split_by_words, calculate_jaundice_rate


class JaundiceRater:

    def __init__(self, dict_path: str):
        self.results = []
        self.charged_words = []
        self.collect_charged_words(dict_path)

    async def rate(self, urls: List[str]):
        async with anyio.create_task_group() as tg:
            for url in urls:
                tg.start_soon(self.process_article, url)

    async def get_article_text(self, url: str):
        async with aiohttp.ClientSession() as self.session:
            html = await self.fetch(url)
        return sanitize(html)

    def collect_charged_words(self, dict_path: str):
        for file in os.listdir(dict_path):
            with open(os.path.join(dict_path, file), encoding='utf8') as f:
                self.charged_words.extend([
                    line.strip() for line in f.readlines()
                ])

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
            if not text:
                raise ArticleNotFound
            async with timeout(3):
                words = split_by_words(pymorphy2.MorphAnalyzer(), text)
        except ClientResponseError:
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
        self.results.append(result)


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'
