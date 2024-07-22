import unittest

from unittest.mock import patch
from aioresponses import aioresponses

from src.api.radistonline.chats import RadistOnlineChats
from src.api.radistonline.contacts import RadistOnlineContacts
from src.core.config import settings, logger


class TestRadistOnlineChats(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_create_new_chat(self, mocked):
        name = "Test User"
        phone = "1234567890"
        url = settings.RADIST_SUBDOMAIN_URL + "messaging/chats/"
        connection_id = settings.CONNECTION_ID
        contact_id = 1
        chat_id = 100

        contact_response = contact_id
        chat_response = {"chat_id": chat_id}

        mocked.post(url, status=200, payload=chat_response)

        with patch.object(RadistOnlineContacts, 'create_contact', return_value=contact_response), \
                patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            result = await RadistOnlineChats.create_new_chat(name, phone)
            self.assertEqual(result, chat_id)
            mock_info.assert_called_with(f"Чат с номером телефона {phone} успешно создан! ID: {chat_id}")
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
