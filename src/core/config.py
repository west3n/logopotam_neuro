import decouple
import logging
import os


class Settings:
    """
    Инициализация константных переменных
    """
    # amoCRM
    AMO_ACCESS_TOKEN: str = decouple.config("AMO_ACCESS_TOKEN")
    AMO_SUBDOMAIN_URL: str = decouple.config('AMO_SUBDOMAIN_URL')

    # radist.online
    RADIST_API_KEY: str = decouple.config('RADIST_API_KEY')
    RADIST_SUBDOMAIN_URL: str = decouple.config('RADIST_SUBDOMAIN_URL')
    RADIST_COMPANY_ID: str = decouple.config('RADIST_COMPANY_ID')

    # OpenAI Assistant
    ASSISTANT_SUBDOMAIN_URL: str = decouple.config('ASSISTANT_SUBDOMAIN_URL')

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI: str = decouple.config("SQLALCHEMY_DATABASE_URI")

    # OpenAI
    OPENAI_API_KEY: str = decouple.config("OPENAI_API_KEY")


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

    ASSISTANT_HEADERS: dict = {
        'Content-Type': 'application/json'
    }


class CustomFormatter(logging.Formatter):
    """
    Создаём кастомный formatter для кастомного loggera для удобного чтения
    """

    def format(self, record):
        separator = '-' * 50
        if record.levelname == 'WARNING':
            record.levelname = 'WEBHOOK'
        return f"{super().format(record)}\n{separator}"


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
        formatter = CustomFormatter('%(asctime)s - %(levelname)s - %(message)s')

        # Создаем обработчик для записи INFO-сообщений в файл logs/info.log
        info_handler = logging.FileHandler(os.path.join(log_folder, 'info.log'))
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(formatter)

        # Создаем обработчик для записи WEBHOOK-сообщений в файл logs/webhook.log
        webhook_handler = logging.FileHandler(os.path.join(log_folder, 'webhook.log'))
        webhook_handler.setLevel(logging.WARNING)
        webhook_handler.setFormatter(formatter)

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
        self.logger.addHandler(webhook_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(critical_handler)

    def info(self, message):
        self.logger.info(message)

    def webhook(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)


logger = CustomLogger()
settings = Settings()
headers = Headers()
