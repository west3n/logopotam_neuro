import asyncio

import aiohttp

from src.api.amoCRM.pipelines import PipelineFetcher
from src.core.config import settings, headers


class LeadFetcher:
    @staticmethod
    async def get_all_leads():
        """
        Получение информации обо всех лидах.

        :return: Список словарей, содержащий информацию о каждом лиде
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                return response_json['_embedded']['leads']

    @staticmethod
    async def get_lead(lead_id: str):
        """
        Получение информации о конкретном лиде.

        :param lead_id: Строка, идентификатор лидера
        :return: Словарь, содержащий информацию о конкретном лиде
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                return await response.json()

    @staticmethod
    async def change_lead_name(lead_id: str, new_name: str):
        """
        Изменение имени лида.

        :param lead_id: Строка, идентификатор лида
        :param new_name: Строка, новое имя для лида
        :return: Строка, сообщение об успешном или неудачном изменении имени
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id)
        data = {
            'name': new_name
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                if response.status == 200:
                    return "Имя изменено успешно!"
                else:
                    return "Возникла проблема при изменении имени!\n" + await response.text()

    @staticmethod
    async def change_lead_status(lead_id: str, status_name: str):
        """
        Изменение статуса лида.

        :param lead_id: Строка, идентификатор лида
        :param status_name: Строка, новый идентификатор статуса для лида
        :return: Строка, сообщение об успешном или неудачном изменении статуса
        """
        status_id = await PipelineFetcher.get_pipeline_status_id_by_name(status_name)
        statuses_dict = await PipelineFetcher.get_pipeline_statuses()
        available_statuses = [value for _, value in statuses_dict.items()]
        if status_id:
            url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id)
            data = {
                'status_id': status_id
            }
            async with (aiohttp.ClientSession() as session):
                async with session.patch(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                    if response.status == 200:
                        return "Статус изменен успешно!"
                    else:
                        return "Возникла проблема при изменении статуса!\n" + await response.text()
        else:
            return f"Данного статуса не существует! Доступные варианты:\n{', '.join(available_statuses)}"


async def amo_leads_list():
    amo_leads = await LeadFetcher.get_all_leads()
    for lead in amo_leads:
        print(lead)


if __name__ == "__main__":
    asyncio.run(amo_leads_list())
