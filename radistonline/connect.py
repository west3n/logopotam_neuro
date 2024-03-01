import asyncio
import aiohttp

from decouple import config


API_KEY = config('API_KEY')
SUBDOMAIN_URL = config('RADIST_API_URL')
COMPANY_ID = config('COMPANY_ID')


class RadistonlineConnect:
    def __init__(self, api_key: str, subdomain_url: str):
        """
        Инициализация объекта класса RadistonlineConnect.

        :param api_key: Строка, токен доступа для аутентификации
        :param subdomain_url: Строка, URL поддомена для API запросов
        """
        self.api_key = api_key
        self.subdomain_url = subdomain_url

    def get_headers(self):
        """
        Формирование заголовков запроса.

        :return: Словарь, содержащий заголовки запроса, включая авторизацию и тип контента
        """
        return {
            'X-Api-Key': f'{self.api_key}',
            'Content-Type': 'application/json'
        }

    async def get_connection_id(self):
        """
        Получение ID подключения, необходим для работы с методами API
        :return: ID в формате целочисленного значения (int)
        """
        url = self.subdomain_url + 'connections/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.get_headers()) as response:
                response_json = await response.json()
                return int(response_json['connections'][0]['id'])

    async def get_all_chats(self):
        """
        Получение всех чатов
        :return: Список всех чатов, каждый чат в формате JSON
        """
        url = self.subdomain_url + 'messaging/chats/with_contacts/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.get_headers()) as response:
                response_json = await response.json()
                return response_json["data"]

    async def send_message(self, chat_id: int):
        """
        Отправка сообщения через chat_id клиента

        :param chat_id: ID чата клиента из списка чатов Radist.Online
        :return: Текст, сообщающий об успешной отправке сообщения (или кода с текстом ошибки)
        """
        url = self.subdomain_url + 'messaging/messages/'
        data = {
            "connection_id": await self.get_connection_id(),
            "chat_id": chat_id,
            "mode": "async",
            "message_type": "text",
            "text": {
                "text": "Все хорошо, как твои дела?"
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=self.get_headers(), json=data) as response:
                if response.status == 200:
                    return "Сообщение успешно отправлено!"
                else:
                    return f"Возникла ошибка {response.status} c текстом:\n{await response.text()}"
