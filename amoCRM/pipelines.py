import aiohttp

from decouple import config

ACCESS_TOKEN = config('ACCESS_TOKEN')
SUBDOMAIN_URL = config('SUBDOMAIN_URL')


class PipelineFetcher:
    def __init__(self, access_token, subdomain_url):
        """
        Инициализация объекта класса PipelineFetcher.

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

    async def get_pipeline_info(self):
        """
        Получение информации обо всех воронках, а так как воронка всего одна, то получаем данные по нулевому индексу.

        :return: Словарь, содержащий информацию о воронке
        """
        url = self.subdomain_url + '/api/v4/leads/pipelines'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.get_headers()) as response:
                if response.status == 200:
                    response_json = await response.json()
                    return response_json['_embedded']['pipelines'][0]
                else:
                    return await response.json()

    async def get_pipeline_statuses(self):
        """
        Получение информации обо всех статусах в воронке.

        :return: Словарь, содержащий информацию о статусах в воронке в формате {id: name}
        """
        pipeline_data = await self.get_pipeline_info()
        pipeline_id = pipeline_data['id']
        url = self.subdomain_url + f'/api/v4/leads/pipelines/{pipeline_id}/statuses'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.get_headers()) as response:
                if response.status == 200:
                    statuses = await response.json()
                    statuses_dict = {}
                    for status in statuses['_embedded']['statuses']:
                        statuses_dict[status['id']] = status['name']
                    return statuses_dict
                else:
                    return await response.json()

    async def get_pipeline_status_id_by_name(self, name):
        """
        Получение id статуса по его имени.

        :param name: Имя статуса
        :return: id статуса, если он найден, иначе None
        """
        statuses_dict = await self.get_pipeline_statuses()
        for status_id, status_name in statuses_dict.items():
            if status_name == name:
                return status_id
        return None
