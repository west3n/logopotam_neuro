import asyncio
import aiohttp

from src.core.config import settings, headers


class CustomFieldsFetcher:
    @staticmethod
    async def get_available_fields():
        """
        Получение возможных тегов в сделках
        :return: Список тегов, каждый в формате JSON
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/custom_fields'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                return response_json['_embedded']['custom_fields']

    @staticmethod
    async def get_lead_fields(lead_id: str):
        """
        Получение списка тегов в конкретной сделке
        :param lead_id: ID сделки в строковом формате
        :return: Список тегов в конкретной сделке
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id) + '?with=contacts'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                fields_list = response_json['custom_fields_values']
                return fields_list


if __name__ == '__main__':
    fields = asyncio.run(CustomFieldsFetcher.get_lead_fields('4279557'))
    print(fields)
