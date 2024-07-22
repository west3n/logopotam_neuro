import datetime
import unittest

from unittest.mock import patch
from aioresponses import aioresponses

from src.api.amoCRM.tasks import TaskFetcher
from src.api.amoCRM.leads import LeadFetcher
from src.core.config import settings, logger


class TestTaskFetcher(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_set_task(self, mocked):
        lead_id = "1"
        task_text = "Follow up on lead"
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/tasks'
        post_response = {}

        lead_response = {
            "id": 1,
            "responsible_user_id": 12345,
            "name": "Lead 1"
        }

        complete_till = int((datetime.datetime.now() + datetime.timedelta(minutes=10)).timestamp())
        data = [
            {
                'responsible_user_id': lead_response['responsible_user_id'],
                'entity_id': int(lead_id),
                'entity_type': 'leads',
                'complete_till': complete_till,
                'text': task_text
            }
        ]

        with patch.object(LeadFetcher, 'get_lead', return_value=lead_response), \
                patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            mocked.post(url, status=200, payload=post_response)
            await TaskFetcher.set_task(lead_id, task_text)
            mock_info.assert_called_with(f'Задача в сделке {lead_id} поставлена')
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
