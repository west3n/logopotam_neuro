import asyncio
import aiohttp

from src.core.config import settings, headers


class WebhookFetcher:
    @staticmethod
    async def get_webhooks():
        url = settings.AMO_SUBDOMAIN_URL + "/api/v4/webhooks"
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                return response_json

    @staticmethod
    async def create_webhook(webhook_url):
        url = settings.AMO_SUBDOMAIN_URL + "/api/v4/webhooks"
        data = {
            "destination": webhook_url,
            "settings": [
                "add_lead",
                "status_lead"
            ]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                if response.status == 200:
                    return f"Подписка на webhook с URL {webhook_url} успешно создана!"
                else:
                    return f"Возникла ошибка {response.status} c текстом:\n{await response.text()}"
