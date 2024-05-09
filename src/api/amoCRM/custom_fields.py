import asyncio

import aiohttp

from src.core.config import settings, headers


class CustomFieldsFetcher:
    @staticmethod
    async def get_available_fields():
        """
        Получение возможных полей в сделках
        :return: Список тегов, каждый в формате JSON
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/custom_fields'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                return response_json['_embedded']['custom_fields']

    @staticmethod
    async def get_survey_lead_fields(lead_id: str):
        """
        Получение списка полей и значений из анкеты в конкретной сделке
        :param lead_id: ID сделки в строковом формате
        :return: Список полей и значений в конкретной сделке
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id) + '?with=contacts'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                fields_list = response_json['custom_fields_values']
                fields_dict = {item['field_name']: item['values'][0]['value'] for item in
                               fields_list} if fields_list else None  # noqa
                return fields_dict

    @staticmethod
    async def get_utm_source(lead_id: str):
        """
        Получение значения utm_source из анкеты в конкретной сделке
        :param lead_id: ID сделки в строковом формате
        :return: Значение utm_source в конкретной сделке
        """
        fields = await CustomFieldsFetcher.get_survey_lead_fields(lead_id)
        try:
            return fields['utm_source']
        except KeyError:
            return None

    @staticmethod
    async def get_child_data(lead_id: str):
        """
        Получение данных из анкеты в конкретной сделке
        :param lead_id: ID сделки в строковом формате
        :return: Словарь с данными из анкеты
        """
        fields = await CustomFieldsFetcher.get_survey_lead_fields(lead_id)
        try:
            child_data = {
                'Имя ребёнка': fields['Имя ребёнка'],
                'Дата рождения': fields['Дата рождения'],
                'Страна/город': fields['Страна/город'],
                'Подробнее о запросе': fields['Подробнее о запросе'],
                'Диагноз (если есть)': fields['Диагноз (если есть)'],
            }
        except KeyError:
            child_data = None

        return child_data

    @staticmethod
    async def save_survey_lead_fields(lead_id: int, child_data: dict):
        """
        Сохраняем полученные данные по анкете через словарь с полученными данными

        :param lead_id: ID сделки
        :param child_data: Словарь с данными, полученными от клиента
        :return:
        """
        data = {'custom_fields_values': []}
        fields_list = [(field['id'], field['name']) for field in await CustomFieldsFetcher.get_available_fields()]

        field_mapping = {
            'child_name': 'Имя ребёнка',
            'child_birth_date': 'Дата рождения',
            'city': 'Страна/город',
            'doctor_enquiry': 'Подробнее о запросе',
            'diagnosis': 'Диагноз (если есть)',
            'segment': "Сегмент"
        }

        for field, field_name in field_mapping.items():
            if field in child_data:
                field_id = None
                for item in fields_list:
                    if item[1] == field_name:
                        field_id = item[0]
                        break

                if field_id is not None:
                    # Переводим datetime в строку, чтобы записать в amoCRM
                    field_value = child_data[field] if field_name != 'Дата рождения' else child_data[field].strftime(
                        '%d-%m-%Y')  # noqa
                    data['custom_fields_values'].append({
                        'field_id': field_id,
                        'field_name': field_name,
                        'values': [{'value': field_value}]
                    })

        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id) + '?with=contacts'
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                if response.status == 200:
                    return await CustomFieldsFetcher.get_survey_lead_fields(str(lead_id))
