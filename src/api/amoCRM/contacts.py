import aiohttp

from src.core.config import settings, headers, logger


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

    @staticmethod
    async def get_contact_number_by_company(contact_id: str):
        """
        Получение номера телефона через компанию, к которой привязан контакт

        :param contact_id: ID контакта в строковом формате
        :return: Номер телефона в строковом формате
        """
        company_id = await ContactFetcher.get_contact_by_id(contact_id)
        company_id = company_id['_embedded']['companies'][0]['id']
        url = settings.AMO_SUBDOMAIN_URL + 'api/v4/companies/' + str(company_id)
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                company_data = await response.json()
                phone_number = next((cfv['values'][0]['value'] for cfv in company_data['custom_fields_values'] if
                                     cfv['field_name'] == 'Телефон'), None)
                return phone_number

    @staticmethod
    async def rename_contact(contact_id: str, new_name: str):
        """
        Переименование контакта

        :param contact_id: ID контакта в строковом формате
        :param new_name: Новое имя контакта
        :return:
        """
        url = settings.AMO_SUBDOMAIN_URL + 'api/v4/contacts/' + str(contact_id)
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, headers=headers.AMO_HEADERS, json={'name': new_name}) as response:
                if response.status == 200:
                    logger.info(f'Контакт {contact_id} переименован. Новое имя: {new_name}')
                else:
                    logger.error(f'Ошибка переименования контакта {contact_id}: {await response.json()}')
