import asyncio
import aiohttp

from src.core.config import settings, headers


class ContactFetcher:
    @staticmethod
    async def get_all_contacts():
        """
        Получение информации обо всех контактах в amoCRM

        :return: Список контактов, каждый из которых в формате JSON
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/contacts'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                return response_json['_embedded']['contacts']


if __name__ == '__main__':
    contacts = asyncio.run(ContactFetcher.get_all_contacts())
    for contact in contacts:
        print(contact)
