import unittest

from unittest.mock import patch
from aioresponses import aioresponses

from src.api.radistonline.messages import RadistonlineMessages
from src.core.config import settings, logger


class TestRadistonlineMessages(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_send_obvious_message(self, mocked):
        lead_id = 1
        chat_id = 123
        text = "Test message"
        url = settings.RADIST_SUBDOMAIN_URL + 'messaging/messages/'
        post_response = {}

        mocked.post(url, status=200, payload=post_response)

        with patch('src.api.amoCRM.custom_fields.CustomFieldsFetcher.message_counter', return_value=None), \
                patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            await RadistonlineMessages.send_obvious_message(lead_id, chat_id, text)
            mock_info.assert_called_with(f"Отправили сообщение! Сделка #{lead_id}: {text}")
            mock_error.assert_not_called()

    @aioresponses()
    async def test_send_message(self, mocked):
        chat_id = 123
        text = "Test message"
        lead_id = 1
        status_id = 66505833
        url = settings.RADIST_SUBDOMAIN_URL + 'messaging/messages/'
        post_response = {}

        mocked.post(url, status=200, payload=post_response)

        with patch('src.orm.crud.amo_leads.AmoLeadsCRUD.get_value_by_chat_id', return_value=lead_id), \
                patch('src.api.amoCRM.leads.LeadFetcher.get_lead_status_id_by_lead_id', return_value=status_id), \
                patch('src.api.amoCRM.custom_fields.CustomFieldsFetcher.get_neuromanager_status_value',
                      return_value="СТАРТ НЕЙРО"), \
                patch('src.api.amoCRM.leads.LeadFetcher.change_lead_status', return_value=None), \
                patch('src.api.amoCRM.custom_fields.CustomFieldsFetcher.message_counter', return_value=None), \
                patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            await RadistonlineMessages.send_message(chat_id, text)
            mock_info.assert_called_with(f"Отправили сообщение! Сделка #{lead_id}: {text}")
            mock_error.assert_not_called()

    @aioresponses()
    async def test_send_image(self, mocked):
        chat_id = 123
        image_url = "https://example.com/image.jpg"
        url = settings.RADIST_SUBDOMAIN_URL + 'messaging/messages/'
        post_response = {}

        mocked.post(url, status=200, payload=post_response)

        with patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            await RadistonlineMessages.send_image(chat_id, image_url)
            mock_info.assert_called_with(f"Картинка успешно отправлена! Чат #{chat_id}")
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
