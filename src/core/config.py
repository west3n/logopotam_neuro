import decouple


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

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI: str = ''


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


settings = Settings()
headers = Headers()
