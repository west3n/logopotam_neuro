import aiohttp

from src.core.config import settings, headers, logger


class TagsFetcher:
    @staticmethod
    async def get_tag_by_name(name: str):
        """
        Получение id тега по имени
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/tags/?filter[name]=' + name
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                tag_id: list = [{'id': response_json['_embedded']['tags'][0]['id']}]
                return tag_id

    @staticmethod
    async def get_old_lead_tags_ids(lead_id: str):
        """
        Получение старых тегов лида
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + lead_id
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                tags: list = response_json['_embedded']['tags']
                old_tags_ids: list = [{'id': tag['id']} for tag in tags]
                return old_tags_ids

    @staticmethod
    async def add_new_tag(lead_id: str, tag_name: str):
        """
        Добавление нового тега к сделке
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + lead_id
        old_tags = await TagsFetcher.get_old_lead_tags_ids(lead_id)
        new_tag_id = await TagsFetcher.get_tag_by_name(tag_name)
        data = {'_embedded': {'tags': old_tags + new_tag_id}}
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, json=data, headers=headers.AMO_HEADERS) as response:
                if response.status == 200:
                    logger.info(f'Тег {tag_name} добавлен к сделке {lead_id}')
                else:
                    logger.error(f'Не удалось добавить тег {tag_name} к сделке {lead_id}: {str(await response.json())}')
