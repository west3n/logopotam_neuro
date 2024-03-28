import asyncio

import aiohttp
import decouple

from src.core.config import settings, headers
from src.api.radistonline.connect import RadistOnlineConnect


class RadistonlineMessages:
    @staticmethod
    async def send_message(chat_id: int, text: str):
        """
        Отправка сообщения через chat_id клиента

        :param chat_id: ID чата клиента из списка чатов Radist.Online
        :param text: Текст сообщения
        :return: Текст, сообщающий об успешной отправке сообщения (или кода с текстом ошибки)
        """
        url = settings.RADIST_SUBDOMAIN_URL + 'messaging/messages/'
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
            async with session.post(url=url, headers=headers.RADIST_HEADERS, json=data) as response:
                if response.status == 200:
                    return "Сообщение успешно отправлено!"
                else:
                    return f"Возникла ошибка {response.status} c текстом:\n{await response.text()}"

    @staticmethod
    async def send_image(chat_id: int, image_url: str, caption=None):
        """
        Отправка картинки через chat_id клиента

        :param chat_id: ID чата клиента из списка чатов Radist.Online
        :param image_url: URL картинки, который берётся через метод upload_file
        :param caption: Подпись к картинке, может быть None
        :return: Текст, сообщающий об успешной отправке сообщения (или кода с текстом ошибки)
        """
        url = settings.RADIST_SUBDOMAIN_URL + 'messaging/messages/'
        data = {
            "connection_id": await RadistOnlineConnect.get_connection_id(),
            "chat_id": chat_id,
            "mode": "async",
            "message_type": "image",
            "image": {
                "caption": '' if not caption else caption,
                "url": image_url
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.RADIST_HEADERS, json=data) as response:
                if response.status == 200:
                    return "Сообщение успешно отправлено!"
                else:
                    return f"Возникла ошибка {response.status} c текстом:\n{await response.text()}"
