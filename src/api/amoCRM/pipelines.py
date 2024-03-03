import aiohttp
from src.core.config import Settings, Headers


class PipelineFetcher:
    @staticmethod
    async def get_pipeline_info():
        """
        Получение информации обо всех воронках, а так как воронка всего одна, то получаем данные по нулевому индексу.

        :return: Словарь, содержащий информацию о воронке
        """
        url = Settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/pipelines'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=Headers.AMO_HEADERS) as response:
                if response.status == 200:
                    response_json = await response.json()
                    return response_json['_embedded']['pipelines'][0]
                else:
                    return await response.json()

    @staticmethod
    async def get_pipeline_statuses():
        """
        Получение информации обо всех статусах в воронке.

        :return: Словарь, содержащий информацию о статусах в воронке в формате {id: name}
        """
        pipeline_data = await PipelineFetcher.get_pipeline_info()
        pipeline_id = pipeline_data['id']
        url = Settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/pipelines/{pipeline_id}/statuses'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=Headers.AMO_HEADERS) as response:
                if response.status == 200:
                    statuses = await response.json()
                    statuses_dict = {}
                    for status in statuses['_embedded']['statuses']:
                        statuses_dict[status['id']] = status['name']
                    return statuses_dict
                else:
                    return await response.json()

    @staticmethod
    async def get_pipeline_status_id_by_name(name: str):
        """
        Получение id статуса по его имени.

        :param name: Имя статуса
        :return: id статуса, если он найден, иначе None
        """
        statuses_dict = await PipelineFetcher.get_pipeline_statuses()
        for status_id, status_name in statuses_dict.items():
            if status_name == name:
                return status_id
        return None
