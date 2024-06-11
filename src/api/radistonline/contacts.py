import aiohttp

from src.core.config import settings, headers, logger


class RadistOnlineContacts:
    @staticmethod
    async def get_contacts():
        """
        Получение информации обо всех контактах
        :return: Список словарей с информацией о контактах
        """
        url = settings.RADIST_SUBDOMAIN_URL + '/contacts/'
        data = {
            'order_by': 'created_at:desc',
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.RADIST_HEADERS, params=data) as response:
                response_json = await response.json()
                return response_json

    @staticmethod
    async def create_contact(name: str, phone: str):
        """
        Создание нового контакта
        :return: Текст с успешным созданием контакта и его ID или текст и код ошибки
        """
        url = settings.RADIST_SUBDOMAIN_URL + '/contacts/'
        data = {'name': name, 'phones': [{'type': "work", 'value': phone}]}
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.RADIST_HEADERS, json=data) as response:
                response_json = await response.json()
                if response.status == 200:
                    logger.info(f"Контакт с номером телефона {phone} успешно создан! ID: {response_json['id']}")
                    return response_json['id']
                else:
                    logger.error(f"Проблема при создании контакта с номером телефона {phone}: {str(response_json)}")
                    return None
