import aiohttp

from decouple import config
from src.core.config import Settings, Headers


class RadistOnlineConnect:
    @staticmethod
    async def get_connection_id():
        """
        Получение ID подключения, необходим для работы с методами API
        :return: ID в формате целочисленного значения (int)
        """
        url = Settings.RADIST_SUBDOMAIN_URL + 'connections/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=Headers.RADIST_HEADERS) as response:
                response_json = await response.json()
                return int(response_json['connections'][0]['id'])

    @staticmethod
    async def get_all_chats():
        """
        Получение всех чатов
        :return: Список всех чатов, каждый чат в формате JSON
        """
        url = Settings.RADIST_SUBDOMAIN_URL + 'messaging/chats/with_contacts/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=Headers.RADIST_HEADERS) as response:
                response_json = await response.json()
                return response_json["data"]

    @staticmethod
    async def send_message(chat_id: int, text: str):
        """
        Отправка сообщения через chat_id клиента

        :param chat_id: ID чата клиента из списка чатов Radist.Online
        :param text: Текст сообщения
        :return: Текст, сообщающий об успешной отправке сообщения (или кода с текстом ошибки)
        """
        url = Settings.RADIST_SUBDOMAIN_URL + 'messaging/messages/'
        data = {
            "connection_id": await RadistOnlineConnect.get_connection_id(),
            "chat_id": chat_id,
            "mode": "async",
            "message_type": "text",
            "text": {
                "text": text
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=Headers.RADIST_HEADERS, json=data) as response:
                if response.status == 200:
                    return "Сообщение успешно отправлено!"
                else:
                    return f"Возникла ошибка {response.status} c текстом:\n{await response.text()}"
