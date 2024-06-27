import aiohttp

from src.core.config import settings, headers, logger


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
        :return: None
        """
        data = {'custom_fields_values': []}
        fields_list = [(field['id'], field['name']) for field in await CustomFieldsFetcher.get_available_fields()]

        for field_name, field_value in child_data.items():
            for item in fields_list:
                if item[1] == field_name:
                    field_id = item[0]
                    data['custom_fields_values'].append({
                        'field_id': field_id,
                        'field_name': field_name,
                        'values': [{'value': field_value}]
                    })
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id) + '?with=contacts'
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                response_json = await response.json()
                if response.status == 200:
                    logger.info(f"Данные анкеты в сделке {lead_id} успешно записаны в amoCRM")
                else:
                    logger.error(f"Ошибка при записи данных в сделке {lead_id}: {str(response_json)}")

    @staticmethod
    async def message_counter(lead_id: int):
        """
        Добавляем + 1 к количеству сообщений в сделке
        :param lead_id: ID сделки
        :return: None
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id) + '?with=contacts'
        field_id = 777980  # ID поля "Нейроменеджер кол-во сообщений"

        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                if response.status == 200:
                    value = 1
                    fields_list = response_json['custom_fields_values']
                    if fields_list:
                        field_ids = [field['field_id'] for field in fields_list]
                        if field_id in field_ids:
                            value = \
                                [int(field['values'][0]['value']) + 1 for field in fields_list if
                                 field['field_id'] == field_id][0]
                        data = {'custom_fields_values': [{'field_id': field_id, 'values': [{'value': str(value)}]}]}
                    else:
                        data = {'custom_fields_values': [{'field_id': field_id, 'values': [{'value': str(value)}]}]}
                    async with session.patch(url=url, headers=headers.AMO_HEADERS, json=data) as new_response:
                        new_response_json = await new_response.json()
                        if new_response.status == 200:
                            logger.info(
                                f"Кол-во сообщений в сделке {lead_id} успешно обновлено. Новое значение: {value}")
                        else:
                            logger.error(
                                f"Ошибка при обновлении кол-ва сообщений в сделке {lead_id}: {str(new_response_json)}")
                else:
                    logger.error(f"Ошибка при обновлении кол-ва сообщений в сделке {lead_id}: {str(response_json)}")

    @staticmethod
    async def change_status(lead_id: int, phone_number: str = None, text: str = None):
        """
        В поле "Нейроменеджер статус" обрабатываемой заявки записываем значение:
        "Ошибка инициализации чата для номера: [НОМЕР]",
        где [НОМЕР] - номер телефона по которому была попытка инициализации чата
        :param text: Текст статуса
        :param lead_id: ID сделки
        :param phone_number: Номер телефона
        :return: None
        """
        if phone_number is None:
            value = text
        else:
            value = f"Ошибка инициализации чата для номера: {phone_number}"
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id) + '?with=contacts'
        field_id = 777978  # ID поля "Нейроменеджер статус"
        data = {
            'custom_fields_values': [
                {
                    'field_id': field_id,
                    'values': [{'value': value}]
                }
            ]
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                response_json = await response.json()
                if response.status == 200:
                    logger.info(f"Поле 'Нейроменеджер статус' в сделке {lead_id} успешно обновлено")
                else:
                    logger.error(
                        f"Ошибка при обновлении поля 'Нейроменеджер статус' в сделке {lead_id}: {str(response_json)}")

    @staticmethod
    async def get_neuromanager_status_value(lead_id: int):
        """
        Возвращает значение поля "Нейроменеджер статус" из анкеты в конкретной сделке
        :param lead_id: ID сделки в строковом формате
        :return: Значение статуса в конкретной сделке
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + str(lead_id) + '?with=contacts'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                if response.status == 200:
                    fields_list = response_json['custom_fields_values']
                    field_ids = [field['field_id'] for field in fields_list]
                    if 777978 in field_ids:
                        field_value = \
                            [field['values'][0]['value'] for field in fields_list if field['field_id'] == 777978][
                                0]
                    else:
                        field_value = None
                    logger.info(f"Поле 'Нейроменеджер статус' в сделке {lead_id} успешно получено: {field_value}")
                    return field_value
                else:
                    logger.error(f"Ошибка при получении значения поля 'Нейроменеджер статус' в сделке {lead_id}: "
                                 f"{str(response_json)}")
                    return None
