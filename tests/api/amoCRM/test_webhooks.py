import unittest

from unittest.mock import patch
from aioresponses import aioresponses

from src.api.amoCRM.webhooks import WebhooksFetcher
from src.core.config import settings, logger


class TestWebhooksFetcher(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_get_webhook_status(self, mocked):
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/webhooks'
        get_response = {
            "_embedded": {
                "webhooks": [
                    {
                        "id": 1,
                        "destination": "http://188.225.60.154:5000/amocrm",
                        "disabled": False
                    },
                    {
                        "id": 2,
                        "destination": "http://example.com/webhook",
                        "disabled": True
                    }
                ]
            }
        }

        mocked.get(url, payload=get_response)

        with patch('builtins.print') as mock_print, \
                patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            await WebhooksFetcher.get_webhook_status()
            mock_print.assert_called_with(False)
            mock_info.assert_called_with('Webhooks получены')
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
