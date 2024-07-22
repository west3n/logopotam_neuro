import unittest

from unittest.mock import patch
from aioresponses import aioresponses

from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.pipelines import PipelineFetcher
from src.core.config import settings, logger


class TestLeadFetcher(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_get_all_leads(self, mocked):
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads?with=contacts'
        leads_response = {
            "_embedded": {
                "leads": [
                    {"id": 1, "name": "Lead 1"},
                    {"id": 2, "name": "Lead 2"}
                ]
            }
        }
        mocked.get(url, payload=leads_response)

        result = await LeadFetcher.get_all_leads()
        self.assertEqual(result, leads_response['_embedded']['leads'])

    @aioresponses()
    async def test_get_lead(self, mocked):
        lead_id = "1"
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + lead_id + '?with=contacts'
        lead_response = {"id": 1, "name": "Lead 1"}
        mocked.get(url, payload=lead_response)

        result = await LeadFetcher.get_lead(lead_id)
        self.assertEqual(result, lead_response)

    @aioresponses()
    async def test_get_lead_status_id_by_lead_id(self, mocked):
        lead_id = "1"
        lead_data = {"status_id": "status_123"}

        with patch.object(LeadFetcher, 'get_lead', return_value=lead_data):
            result = await LeadFetcher.get_lead_status_id_by_lead_id(lead_id)
            self.assertEqual(result, "status_123")

    @aioresponses()
    async def test_change_lead_name(self, mocked):
        lead_id = "1"
        new_name = "New Lead Name"
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/' + lead_id
        patch_response = {}
        mocked.patch(url, status=200, payload=patch_response)

        with patch.object(logger, 'info') as mock_info, patch.object(logger, 'error') as mock_error:
            await LeadFetcher.change_lead_name(lead_id, new_name)
            mock_info.assert_called_with(f"Имя лида {lead_id} успешно изменено. Новое имя: {new_name}")
            mock_error.assert_not_called()

    @aioresponses()
    async def test_change_lead_status(self, mocked):
        lead_id = 1
        status_name = "СТАРТ НЕЙРО"
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/{lead_id}'
        patch_response = {}

        with patch.object(PipelineFetcher, 'get_pipeline_status_id_by_name', return_value="status_123"), \
                patch.object(PipelineFetcher, 'get_pipeline_statuses', return_value={"status_123": "СТАРТ НЕЙРО"}), \
                patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            mocked.patch(url, status=200, payload=patch_response)
            await LeadFetcher.change_lead_status(lead_id, status_name)
            mock_info.assert_called_with(f"Статус лида {lead_id} успешно изменен. Новый статус: {status_name}")
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
