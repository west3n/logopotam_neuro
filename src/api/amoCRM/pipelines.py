import aiohttp

from src.core.config import settings, headers


class PipelineFetcher:
    @staticmethod
    async def get_pipelines():
        """
        Получение информации обо всех воронках.

        :return: Словарь, содержащий информацию о воронке
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/pipelines'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                if response.status == 200:
                    response_json = await response.json()
                    return response_json['_embedded']['pipelines']
                else:
                    return await response.json()

    @staticmethod
    async def get_pipeline_statuses():
        """
        Получение информации обо всех статусах в воронке.

        :return: Словарь, содержащий информацию о статусах в воронке в формате {id: name}
        """
        pipeline_id = settings.LOGOPOTAM_PIPELINE_ID
        statuses_dict = {}
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/pipelines/{pipeline_id}/statuses'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                statuses = await response.json()
                for status in statuses['_embedded']['statuses']:
                    statuses_dict[status['id']] = (pipeline_id, status['name'])
                return statuses_dict

    @staticmethod
    async def get_pipeline_id_by_name(name: str):
        """
        Получение id воронки по его имени.

        :param name: Имя воронки
        :return: id воронки, если он найден, иначе None
        """
        all_pipelines = await PipelineFetcher.get_pipelines()
        pipe_dict = {pipeline['id']: pipeline['name'] for pipeline in all_pipelines}
        pipe_id = next((pipe_id for pipe_id, pipe_name in pipe_dict.items() if pipe_name == name), None)
        return pipe_id

    @staticmethod
    async def get_pipeline_status_id_by_name(name: str):
        """
        Получение id статуса по его имени.

        :param name: Имя статуса
        :return: id статуса, если он найден, иначе None
        """
        statuses_dict = await PipelineFetcher.get_pipeline_statuses()
        for status_id, status_name in statuses_dict.items():
            if name in status_name:
                return status_id
        return None

    @staticmethod
    async def get_pipeline_status_name_by_id(status_id: int):
        """
        Получение имени статуса по его ID.

        :param status_id: ID статуса
        :return: Имя статуса, если найдено, иначе None
        """
        statuses_dict = await PipelineFetcher.get_pipeline_statuses()
        _, status_name = statuses_dict.get(status_id)
        return status_name


if __name__ == '__main__':
    import asyncio

    statuses = asyncio.run(PipelineFetcher.get_pipeline_status_name_by_id(34884795))
    print(statuses)
