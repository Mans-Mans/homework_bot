import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import OutStatusError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    format='%(asctime)s, %(levelname)s, %(message)s',
    level=logging.INFO,
    filename='main.log',
    filemode='w'
)


def check_tokens():
    """Проверка переменных окружения."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logging.critical('Проверьте наличие всех переменных окружения')
        raise False
    return True


def send_message(bot: telegram.bot, message: str) -> str:
    """Функция отправки сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение успешно отправлено')
    except telegram.error.TelegramError:
        logging.error('Ошибка при отправке сообщения')


def get_api_answer(current_timestamp: dict) -> dict:
    """Запрашивает и возвращает API ответ."""
    payload = {'from_date': current_timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=payload)
        response = homework_statuses.json()
    except requests.RequestException:
        logging.error('Ошибка при получении ответа API')
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error('Эндпоинт не доступен')
        raise ('Эндпоинт не доступен')
    return response


def check_response(response: dict) -> list:
    """Проверяет ответ API на соответствие документации."""
    logging.debug('Проверка API')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарём')
    homework = response.get('homeworks')
    if not homework:
        raise KeyError('Ключ "homeworks" не найден')
    if not isinstance(homework, list):
        raise TypeError('Обьект "homework" не является списком')
    return homework[0]


def parse_status(homework: list) -> str:
    """Проверяет статус проверки работы."""
    if 'homework_name' not in homework:
        raise KeyError('Нет домашки"')
    if 'status' not in homework:
        raise KeyError('Не найден статус домашки')
    homework_name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise OutStatusError('Не известный статус работы')
    verdict = HOMEWORK_VERDICTS[status]
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(1)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_status = ''
    current_status = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                current_status = parse_status(homework)
                if current_status != old_status:
                    send_message(bot, current_status)
                    old_status = current_status
                logging.DEBUG('Отсутсвует новый статус')
            logging.info('Сообщение отправлено')
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
