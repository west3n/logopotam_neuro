import unittest

from unittest.mock import patch
from aioresponses import aioresponses

from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.core.config import settings, logger


class TestCustomFieldsFetcher(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_get_available_fields(self, mocked):
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/custom_fields'
        fields_response = {
            "_embedded": {
                "custom_fields": [
                    {"id": 1, "name": "Field 1"},
                    {"id": 2, "name": "Field 2"}
                ]
            }
        }
        mocked.get(url, payload=fields_response)

        result = await CustomFieldsFetcher.get_available_fields()
        self.assertEqual(result, fields_response['_embedded']['custom_fields'])

    @aioresponses()
    async def test_get_survey_lead_fields(self, mocked):
        lead_id = "1"
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/{lead_id}?with=contacts'
        lead_response = {
            "custom_fields_values": [
                {"field_name": "Field 1", "values": [{"value": "Value 1"}]},
                {"field_name": "Field 2", "values": [{"value": "Value 2"}]}
            ]
        }
        mocked.get(url, payload=lead_response)

        result = await CustomFieldsFetcher.get_survey_lead_fields(lead_id)
        expected = {"Field 1": "Value 1", "Field 2": "Value 2"}
        self.assertEqual(result, expected)

    @aioresponses()
    async def test_get_utm_source(self):
        lead_id = "1"
        survey_fields = {"utm_source": "Flocktory"}

        with patch.object(CustomFieldsFetcher, 'get_survey_lead_fields', return_value=survey_fields):
            result = await CustomFieldsFetcher.get_utm_source(lead_id)
            self.assertEqual(result, "Flocktory")

    @aioresponses()
    async def test_get_child_data(self):
        lead_id = "1"
        survey_fields = {
            "Имя ребёнка": "Вася",
            "Дата рождения": "01-01-2010",
            "Страна/город": "Москва",
            "Подробнее о запросе": "Заикаемся",
            "Диагноз (если есть)": "Диагноза нет",
        }

        with patch.object(CustomFieldsFetcher, 'get_survey_lead_fields', return_value=survey_fields):
            result = await CustomFieldsFetcher.get_child_data(lead_id)
            self.assertEqual(result, survey_fields)

    @aioresponses()
    async def test_save_survey_lead_fields(self, mocked):
        lead_id = 1
        child_data = {
            "Field 1": "Value 1",
            "Field 2": "Value 2"
        }
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/{lead_id}?with=contacts'
        available_fields = [
            {"id": 1, "name": "Field 1"},
            {"id": 2, "name": "Field 2"}
        ]

        with patch.object(CustomFieldsFetcher, 'get_available_fields', return_value=available_fields), \
                patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            mocked.patch(url, status=200, payload={})
            await CustomFieldsFetcher.save_survey_lead_fields(lead_id, child_data)
            mock_info.assert_called_with(f"Данные анкеты в сделке {lead_id} успешно записаны в amoCRM")
            mock_error.assert_not_called()

    @aioresponses()
    async def test_message_counter(self, mocked):
        lead_id = 1
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/{lead_id}?with=contacts'
        lead_response = {
            "custom_fields_values": [
                {"field_id": 777980, "values": [{"value": "1"}]}
            ]
        }
        mocked.get(url, payload=lead_response)

        mocked.patch(url, status=200, payload={})
        with patch.object(logger, 'info') as mock_info, patch.object(logger, 'error') as mock_error:
            await CustomFieldsFetcher.message_counter(lead_id)
            mock_info.assert_called_with(f"Кол-во сообщений в сделке {lead_id} успешно обновлено. Новое значение: 2")
            mock_error.assert_not_called()

    @aioresponses()
    async def test_change_status(self, mocked):
        lead_id = 1
        phone_number = "123456789"
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/{lead_id}?with=contacts'

        mocked.patch(url, status=200, payload={})
        with patch.object(logger, 'info') as mock_info, patch.object(logger, 'error') as mock_error:
            await CustomFieldsFetcher.change_status(lead_id, phone_number)
            mock_info.assert_called_with(f"Поле 'Нейроменеджер статус' в сделке {lead_id} успешно обновлено")
            mock_error.assert_not_called()

    @aioresponses()
    async def test_get_neuromanager_status_value(self, mocked):
        lead_id = 1
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/{lead_id}?with=contacts'
        lead_response = {
            "custom_fields_values": [
                {"field_id": 777978, "values": [{"value": "status_value"}]}
            ]
        }
        mocked.get(url, payload=lead_response)

        with patch.object(logger, 'info') as mock_info, patch.object(logger, 'error') as mock_error:
            result = await CustomFieldsFetcher.get_neuromanager_status_value(lead_id)
            self.assertEqual(result, "status_value")
            mock_info.assert_called_with(
                f"Поле 'Нейроменеджер статус' в сделке {lead_id} успешно получено: status_value")
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
