import asyncio
import aiohttp

from src.core.config import settings, headers
from urllib.parse import quote


class ContactFetcher:
    @staticmethod
    async def get_all_contacts():
        """
        Получение информации обо всех контактах в amoCRM

        :return: Список контактов, каждый из которых в формате JSON
        """
        url = settings.AMO_SUBDOMAIN_URL + 'api/v4/contacts'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                return response_json['_embedded']['contacts']

    @staticmethod
    async def find_existing_phone_number(phone_number: str):
        """
        Проверяем, существует ли уже номер телефона нового контакта в других контактах
        :param phone_number: Номер нового контакта
        """
        encoded_phone = quote(phone_number, safe='')
        url = settings.AMO_SUBDOMAIN_URL + f'api/v4/contacts?filter[custom_fields_values][453541][]={encoded_phone}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                try:
                    response_json = await response.json()
                except aiohttp.ContentTypeError:
                    return False
                return response_json is not None

    @staticmethod
    async def get_contact_by_id(contact_id: str):
        """
        Получение информации о контакте через его ID

        :param contact_id: ID контакта в строковом формате
        :return:
        """
        url = settings.AMO_SUBDOMAIN_URL + 'api/v4/contacts/' + str(contact_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                return await response.json()


if __name__ == '__main__':
    # contacts = asyncio.run(ContactFetcher.get_all_contacts())
    # print(contacts)

    is_contact_exist = asyncio.run(ContactFetcher.find_existing_phone_number("+7 (918) 892-1817"))
    print(is_contact_exist)
