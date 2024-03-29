import aiohttp

from src.core.config import settings, headers


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
    async def check_contact_already_exist_by_phone(contact_id: int, phone_number: str):
        """
        Проверяем, существует ли уже номер телефона нового контакта в других контактах
        :param contact_id:
        :param phone_number:
        :return:
        """
        all_contacts = await ContactFetcher.get_all_contacts()
        phone_numbers = [contact['custom_fields_values'][0]['values'][0]['value'] for contact in all_contacts if contact['id'] != contact_id] # noqa
        return phone_number in phone_numbers

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
