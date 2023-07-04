import asyncio
import logging
import string
import time

import pymorphy2


def timer(func):
    async def wrapper(*args, **kwargs):
        started_at = time.monotonic()
        result = await func(*args, **kwargs)
        finished_at = time.monotonic()
        logging.info(f'Анализ закончен за {finished_at - started_at} сек.')
        return result

    return wrapper


def _clean_word(word):
    for symbol in '«»…:;':
        word = word.replace(symbol, '')
    word = word.strip(string.punctuation)
    return word


@timer
async def split_by_words(morph, text):
    """Учитывает знаки пунктуации, регистр и словоформы, выкидывает предлоги."""
    words = []
    for word in text.split():
        cleaned_word = _clean_word(word)
        normalized_word = morph.parse(cleaned_word)[0].normal_form
        if len(normalized_word) > 2 or normalized_word == 'не':
            words.append(normalized_word)
        await asyncio.sleep(0)
    return words


def calculate_jaundice_rate(article_words, charged_words):
    """Расчитывает желтушность текста, принимает список "заряженных" слов и ищет их внутри article_words."""

    if not article_words:
        return 0.0

    found_charged_words = [word for word in article_words if word in set(charged_words)]
    score = len(found_charged_words) / len(article_words) * 100
    return round(score, 2)


def test_split_by_words():
    # Экземпляры MorphAnalyzer занимают 10-15Мб RAM т.к. загружают в память много данных
    # Старайтесь организовать свой код так, чтоб создавать экземпляр MorphAnalyzer заранее и в единственном числе
    morph = pymorphy2.MorphAnalyzer()

    assert split_by_words(morph, 'Во-первых, он хочет, чтобы') == ['во-первых', 'хотеть', 'чтобы']

    assert split_by_words(morph, '«Удивительно, но это стало началом!»') == ['удивительно', 'это', 'стать', 'начало']


def test_calculate_jaundice_rate():
    assert -0.01 < calculate_jaundice_rate([], []) < 0.01
    assert 33.0 < calculate_jaundice_rate(['все', 'аутсайдер', 'побег'], ['аутсайдер', 'банкротство']) < 34.0
