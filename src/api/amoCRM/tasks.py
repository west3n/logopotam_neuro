import datetime
import aiohttp

from src.core.config import settings, headers, logger
from src.api.amoCRM.leads import LeadFetcher


class TaskFetcher:
    @staticmethod
    async def set_task(lead_id: str, task_text: str):
        """
        Постановка задачи в сделку
        :return: None
        """
        lead = await LeadFetcher.get_lead(lead_id)
        responsible_user_id = lead['responsible_user_id']
        complete_till = int((datetime.datetime.now() + datetime.timedelta(minutes=10)).timestamp())
        data = [
            {
                'responsible_user_id': responsible_user_id,
                'entity_id': int(lead_id),
                'entity_type': 'leads',
                'complete_till': complete_till,
                'text': task_text
            }
        ]
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/tasks'
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                if response.status == 200:
                    logger.info(f'Задача в сделке {lead_id} поставлена')
                else:
                    logger.error(f'Проблема при постановке задачи в сделке {lead_id} : {str(await response.json())}')
