import aiohttp

from src.core.config import settings, headers, logger


class WebhooksFetcher:
    @staticmethod
    async def get_webhook_status():
        """
        Запрос на получение webhooks
        :return: None
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/webhooks'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                if response.status == 200:
                    webhooks = await response.json()
                    for webhook in webhooks['_embedded']['webhooks']:
                        if webhook['destination'] == 'http://188.225.60.154:5000/amocrm':
                            is_webhook_disabled = webhook['disabled']
                            print(is_webhook_disabled)
                    logger.info(f'Webhooks получены')
                else:
                    logger.error(f'Проблема при получении webhooks : {str(await response.json())}')
