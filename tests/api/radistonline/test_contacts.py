import unittest

from unittest.mock import patch
from aioresponses import aioresponses

from src.api.radistonline.contacts import RadistOnlineContacts
from src.core.config import settings, logger


class TestRadistOnlineContacts(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_get_contacts(self, mocked):
        base_url = settings.RADIST_SUBDOMAIN_URL + '/contacts/'
        url = f"{base_url}?order_by=created_at:desc"
        get_response = [
            {"id": 1, "name": "Contact 1"},
            {"id": 2, "name": "Contact 2"}
        ]

        mocked.get(url, payload=get_response)

        result = await RadistOnlineContacts.get_contacts()
        self.assertEqual(result, get_response)

    @aioresponses()
    async def test_create_contact(self, mocked):
        url = settings.RADIST_SUBDOMAIN_URL + '/contacts/'
        name = "Test User"
        phone = "1234567890"
        post_response = {"id": 1}

        mocked.post(url, status=200, payload=post_response)

        with patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            result = await RadistOnlineContacts.create_contact(name, phone)
            self.assertEqual(result, 1)
            mock_info.assert_called_with(
                f"Контакт с номером телефона {phone} успешно создан! ID: {post_response['id']}")
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
