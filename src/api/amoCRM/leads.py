import aiohttp
from aiohttp import ContentTypeError

from src.api.amoCRM.pipelines import PipelineFetcher
from src.core.config import settings, headers, logger


class LeadFetcher:
    @staticmethod
    async def get_all_leads() -> list:
        """
        Получение информации обо всех лидах.

        :return: Список словарей, содержащий информацию о каждом лиде
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads?with=contacts'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                return response_json['_embedded']['leads']

    @staticmethod
    async def get_lead(lead_id: str) -> dict:
        """
        Получение информации о конкретном лиде.

        :param lead_id: Строка, идентификатор лидера
        :return: Словарь, содержащий информацию о конкретном лиде
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id) + '?with=contacts'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                return await response.json()

    @staticmethod
    async def get_lead_status_id_by_lead_id(lead_id: str) -> str | None:
        """
        Получение идентификатора статуса для конкретного лида.

        :param lead_id: Строка, идентификатор лида
        :return: Строка, идентификатор статуса для конкретного лида
        """
        try:
            lead_data = await LeadFetcher.get_lead(lead_id)
            return lead_data['status_id']
        except ContentTypeError as e:
            logger.error(f"Не удалось получить статус сделки с ID {lead_id}: {e}")
            return None

    @staticmethod
    async def change_lead_name(lead_id: str, new_name: str) -> None:
        """
        Изменение имени лида.

        :param lead_id: Строка, идентификатор лида
        :param new_name: Строка, новое имя для лида
        :return: Сообщение об успешном или неудачном изменении имени
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id)
        data = {
            'name': new_name
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                if response.status == 200:
                    logger.info(f"Имя лида {lead_id} успешно изменено. Новое имя: {new_name}")
                else:
                    logger.error(f"Ошибка при изменении имени лида {lead_id}: {str(await response.json())}")

    @staticmethod
    async def change_lead_status(lead_id: int, status_name: str) -> None:
        """
        Изменение статуса лида.

        :param lead_id: Строка, идентификатор лида
        :param status_name: Строка, новый идентификатор статуса для лида
        :return: Сообщение об успешном или неудачном изменении статуса
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
                        logger.info(f"Статус лида {lead_id} успешно изменен. Новый статус: {status_name}")
                    else:
                        logger.error(f"Ошибка при изменении статуса лида {lead_id}: {str(await response.json())}")
        else:
            logger.error(f"Статус {status_name} не найден. Доступные статусы: {available_statuses}")
