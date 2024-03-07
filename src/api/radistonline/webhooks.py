import asyncio

import aiohttp

from src.api.radistonline.connect import RadistOnlineConnect
from src.core.config import settings, headers


class RadistOnlineWebhook:
    @staticmethod
    async def get_webhooks():
        """
        Получение всех активных вебхуков
        :return: Список вебхуков
        """
        url = settings.RADIST_SUBDOMAIN_URL + '/webhooks'
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.RADIST_HEADERS) as response:
                return await response.json()

    @staticmethod
    async def create_webhook(webhook_url: str):
        """
        Создание подписки на новый webhook для всех видов events

        :return: Текст с успешным созданием новой подписки (или код ошибки с текстом ошибки)
        """
        url = settings.RADIST_SUBDOMAIN_URL + '/webhooks'
        connection_id = await RadistOnlineConnect.get_connection_id()
        data = {
            "url": webhook_url,
            "events": [
                "messages.create",
                'messages.delivery.delivered',
                'messages.delivery.read',
                'messages.delivery.error'
            ],
            "connection_id": connection_id
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.RADIST_HEADERS, json=data) as response:
                if response.status == 200:
                    return f"Подписка на webhook с URL {webhook_url} успешно создана!"
                else:
                    return f"Возникла ошибка {response.status} c текстом:\n{await response.text()}"
