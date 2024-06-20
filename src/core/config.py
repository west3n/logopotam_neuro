import traceback
import instructor
import decouple
import logging
import os

from openai import OpenAI, AsyncOpenAI


class Settings:
    """
    Инициализация константных переменных
    """
    # amoCRM
    AMO_ACCESS_TOKEN: str = decouple.config("AMO_ACCESS_TOKEN")
    AMO_SUBDOMAIN_URL: str = decouple.config('AMO_SUBDOMAIN_URL')
    LOGOPOTAM_PIPELINE_ID: int = int(decouple.config('LOGOPOTAM_PIPELINE_ID'))
    PHONE_NUMBER_FIELD_ID: int = int(decouple.config('PHONE_NUMBER_FIELD_ID'))

    # radist.online
    RADIST_API_KEY: str = decouple.config('RADIST_API_KEY')
    RADIST_SUBDOMAIN_URL: str = decouple.config('RADIST_SUBDOMAIN_URL')
    RADIST_COMPANY_ID: str = decouple.config('RADIST_COMPANY_ID')
    ZOOM_IMAGE_URL: str = decouple.config("ZOOM_IMAGE_URL")
    CONNECTION_ID: int = int(decouple.config("CONNECTION_ID"))

    # bubulearn
    BUBULEARN_API_KEY: str = decouple.config("BUBULEARN_API_KEY")
    BUBULEARN_SUBDOMAIN_URL: str = decouple.config("BUBULEARN_SUBDOMAIN_URL")

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI: str = decouple.config("SQLALCHEMY_DATABASE_URI")

    # OpenAI
    OPENAI_API_KEY: str = decouple.config("OPENAI_API_KEY")
    OPENAI_ASSISTANT_ID: str = decouple.config("OPENAI_ASSISTANT_ID")
    OPENAI_REGISTRATION_ASSISTANT_ID: str = decouple.config("OPENAI_REGISTRATION_ASSISTANT_ID")


class Headers:
    """
    Инициализация headers для API-запросов
    """
    AMO_HEADERS: dict = {
        'Authorization': f'Bearer {Settings.AMO_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    RADIST_HEADERS: dict = {
        'X-Api-Key': f'{Settings.RADIST_API_KEY}',
        'Content-Type': 'application/json'
    }
    BUBULEARN_HEADERS: dict = {
        'Authorization': f'Bearer {Settings.BUBULEARN_API_KEY}',
    }


class OpenaiClients:
    """
    Инициализация различных клиентов OpenAI
    """
    OPENAI_CLIENT = OpenAI(
        api_key=Settings.OPENAI_API_KEY
    )
    OPENAI_ASYNC_CLIENT = AsyncOpenAI(
        api_key=Settings.OPENAI_API_KEY
    )
    OPENAI_INSTRUCTOR_CLIENT = instructor.patch(
        client=OpenAI(
            api_key=Settings.OPENAI_API_KEY
        )
    )
    OPENAI_ASYNC_INSTRUCTOR_CLIENT = instructor.patch(
        client=AsyncOpenAI(
            api_key=Settings.OPENAI_API_KEY
        )
    )


class CustomLogger:
    """
    Создаём кастомный logger, который будет записывать логи в разные файлы в зависимости от его уровня
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        log_folder = '/script/logs'

        # Создаем папку для хранения логов, если ее нет
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        # Создаем форматтер для сообщений лога с разделителем
        separator = '-' * 50
        formatter = logging.Formatter(f'%(asctime)s - %(levelname)s - %(message)s\n{separator}')

        # Создаем обработчик для записи INFO-сообщений в файл logs/info.log
        info_handler = logging.FileHandler(os.path.join(log_folder, 'info.log'))
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)

        # Создаем обработчик для записи WARNING-сообщений в файл logs/warning.log
        warning_handler = logging.FileHandler(os.path.join(log_folder, 'warning.log'))
        warning_handler.setLevel(logging.WARNING)
        warning_handler.setFormatter(formatter)

        # Создаем обработчик для записи ERROR-сообщений в файл logs/error.log
        error_handler = logging.FileHandler(os.path.join(log_folder, 'error.log'))
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        # Создаем обработчик для записи CRITICAL-сообщений в файл logs/critical.log
        critical_handler = logging.FileHandler(os.path.join(log_folder, 'critical.log'))
        critical_handler.setLevel(logging.CRITICAL)
        critical_handler.setFormatter(formatter)

        # Добавляем обработчики к логгеру
        self.logger.addHandler(info_handler)
        self.logger.addHandler(warning_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(critical_handler)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        message = f"{message}\n{traceback.format_exc()}"
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)


logger = CustomLogger()
settings = Settings()
headers = Headers()
openai_clients = OpenaiClients()
