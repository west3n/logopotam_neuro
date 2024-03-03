import aiohttp

from src.api.radistonline.connect import RadistOnlineConnect
from src.core.config import Settings, Headers


class RadistOnlineWebhook:
    @staticmethod
    async def create_webhook(webhook_url: str):
        """
        Создание подписки на новый webhook для всех видов events

        :return: Текст с успешным созданием новой подписки (или код ошибки с текстом ошибки)
        """
        url = Settings.RADIST_SUBDOMAIN_URL + '/webhooks'
        connection_id = RadistOnlineConnect.get_connection_id()
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
            async with session.post(url=url, headers=Headers.RADIST_HEADERS, json=data) as response:
                if response.status == 200:
                    return f"Подписка на webhook с URL {webhook_url} успешно создана!"
                else:
                    return f"Возникла ошибка {response.status} c текстом:\n{await response.text()}"
