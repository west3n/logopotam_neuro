import asyncio
import aiohttp

from decouple import config
from amoCRM.pipelines import PipelineFetcher

ACCESS_TOKEN = config('ACCESS_TOKEN')
SUBDOMAIN_URL = config('SUBDOMAIN_URL')


class LeadFetcher:
    def __init__(self, access_token: str, subdomain_url: str):
        """
        Инициализация объекта класса LeadFetcher.

        :param access_token: Строка, токен доступа для аутентификации
        :param subdomain_url: Строка, URL поддомена для API запросов
        """
        self.access_token = access_token
        self.subdomain_url = subdomain_url

    def get_headers(self):
        """
        Формирование заголовков запроса.

        :return: Словарь, содержащий заголовки запроса, включая авторизацию и тип контента
        """
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    async def get_all_leads(self):
        """
        Получение информации обо всех лидах.

        :return: Список словарей, содержащий информацию о каждом лиде
        """
        url = self.subdomain_url + '/api/v4/leads'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.get_headers()) as response:
                response_json = await response.json()
                return response_json['_embedded']['leads']

    async def get_lead(self, lead_id: str):
        """
        Получение информации о конкретном лиде.

        :param lead_id: Строка, идентификатор лидера
        :return: Словарь, содержащий информацию о конкретном лиде
        """
        url = self.subdomain_url + '/api/v4/leads/' + str(lead_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.get_headers()) as response:
                return await response.json()

    async def change_lead_name(self, lead_id: str, new_name: str):
        """
        Изменение имени лида.

        :param lead_id: Строка, идентификатор лида
        :param new_name: Строка, новое имя для лида
        :return: Строка, сообщение об успешном или неудачном изменении имени
        """
        url = self.subdomain_url + '/api/v4/leads/' + str(lead_id)
        data = {'name': new_name}
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, headers=self.get_headers(), json=data) as response:
                if response.status == 200:
                    return "Имя изменено успешно!"
                else:
                    return "Возникла проблема при изменении имени!\n" + await response.text()

    async def change_lead_status(self, lead_id: str, status_name: str):
        """
        Изменение статуса лида.

        :param lead_id: Строка, идентификатор лида
        :param status_name: Строка, новый идентификатор статуса для лида
        :return: Строка, сообщение об успешном или неудачном изменении статуса
        """
        pipeline_fetcher = PipelineFetcher(self.access_token, self.subdomain_url)
        status_id = await pipeline_fetcher.get_pipeline_status_id_by_name(status_name)
        statuses_dict = await pipeline_fetcher.get_pipeline_statuses()
        available_statuses = [value for _, value in statuses_dict.items()]
        if status_id:
            url = self.subdomain_url + '/api/v4/leads/' + str(lead_id)
            data = {'status_id': status_id}
            async with (aiohttp.ClientSession() as session):
                async with session.patch(url=url, headers=self.get_headers(), json=data) as response:
                    if response.status == 200:
                        return "Статус изменен успешно!"
                    else:
                        return "Возникла проблема при изменении статуса!\n" + await response.text()
        else:
            return f"Данного статуса не существует! Доступные варианты:\n{', '.join(available_statuses)}"
