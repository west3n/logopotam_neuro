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
        field_id = settings.PHONE_NUMBER_FIELD_ID
        url = settings.AMO_SUBDOMAIN_URL + f'api/v4/contacts?filter[custom_fields_values][{field_id}][]={encoded_phone}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                try:
                    response_json = await response.json()
                    if response_json['title'] == 'Bad Request':
                        return False
                except KeyError:
                    contacts = response_json['_embedded']['contacts']
                    return True if len(contacts) > 1 else False
                except (aiohttp.ContentTypeError, KeyError):
                    return False

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
