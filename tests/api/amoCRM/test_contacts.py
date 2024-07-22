import unittest

from unittest.mock import patch
from aioresponses import aioresponses

from src.api.amoCRM.contacts import ContactFetcher
from src.core.config import settings, logger


class TestContactFetcher(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_get_all_contacts(self, mocked):
        url = settings.AMO_SUBDOMAIN_URL + 'api/v4/contacts'
        contacts_response = {
            "_embedded": {
                "contacts": [
                    {"id": 1, "name": "Иванов Иван Иванович"},
                    {"id": 2, "name": "Петров Петр Петрович"}
                ]
            }
        }
        mocked.get(url, payload=contacts_response)

        result = await ContactFetcher.get_all_contacts()
        self.assertEqual(result, contacts_response['_embedded']['contacts'])

    @aioresponses()
    async def test_get_contact_by_id(self, mocked):
        contact_id = "1"
        url = settings.AMO_SUBDOMAIN_URL + 'api/v4/contacts/' + contact_id
        contact_response = {"id": 1, "name": "Contact 1"}
        mocked.get(url, payload=contact_response)

        result = await ContactFetcher.get_contact_by_id(contact_id)
        self.assertEqual(result, contact_response)

    @aioresponses()
    async def test_get_contact_number_by_company(self, mocked):
        contact_id = "1"
        contact_url = settings.AMO_SUBDOMAIN_URL + 'api/v4/contacts/' + contact_id
        contact_response = {
            "_embedded": {
                "companies": [
                    {"id": 1}
                ]
            }
        }
        company_url = settings.AMO_SUBDOMAIN_URL + 'api/v4/companies/1'
        company_response = {
            "custom_fields_values": [
                {
                    "field_name": "Телефон",
                    "values": [
                        {"value": "123456789"}
                    ]
                }
            ]
        }
        mocked.get(contact_url, payload=contact_response)
        mocked.get(company_url, payload=company_response)

        result = await ContactFetcher.get_contact_number_by_company(contact_id)
        self.assertEqual(result, "123456789")

    @aioresponses()
    async def test_rename_contact(self, mocked):
        contact_id = "1"
        new_name = "Иванов Иван Иванович"
        url = settings.AMO_SUBDOMAIN_URL + 'api/v4/contacts/' + contact_id
        patch_response = {}
        mocked.patch(url, status=200, payload=patch_response)

        with patch.object(logger, 'info') as mock_info, patch.object(logger, 'error') as mock_error:
            await ContactFetcher.rename_contact(contact_id, new_name)
            mock_info.assert_called_with(f'Контакт {contact_id} переименован. Новое имя: {new_name}')
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
