import logging
import string
import time


def timer(func):
    def wrapper(*args, **kwargs):
        started_at = time.monotonic()
        result = func(*args, **kwargs)
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
def split_by_words(morph, text):
    """Учитывает знаки пунктуации, регистр и словоформы, выкидывает предлоги."""
    words = []
    for word in text.split():
        cleaned_word = _clean_word(word)
        normalized_word = morph.parse(cleaned_word)[0].normal_form
        if len(normalized_word) > 2 or normalized_word == 'не':
            words.append(normalized_word)
    return words


def calculate_jaundice_rate(article_words, charged_words):
    """Расчитывает желтушность текста, принимает список "заряженных" слов и ищет их внутри article_words."""

    if not article_words:
        return 0.0

    found_charged_words = [word for word in article_words if word in set(charged_words)]
    score = len(found_charged_words) / len(article_words) * 100
    return round(score, 2)
