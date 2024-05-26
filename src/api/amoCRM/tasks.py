import datetime
import aiohttp

from src.core.config import settings, headers, logger
from src.api.amoCRM.leads import LeadFetcher


class TaskFetcher:
    @staticmethod
    async def set_task(lead_id: str, task_text: str):
        """
        Постановка задачи
        :return: Строка, сообщение об успешном или неудачном изменении статуса задачи
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
                    print(f'Задача в сделке с идентификатором {lead_id} поставлена')
                    logger.info(f'Задача в сделке с идентификатором {lead_id} поставлена')
                else:
                    print(
                        f'Возникла проблема при постановке задачи в сделку с идентификатором {lead_id} : {await response.text()}')
                    logger.error(
                        f'Возникла проблема при постановке задачи в сделку с идентификатором {lead_id} : {await response.text()}')

