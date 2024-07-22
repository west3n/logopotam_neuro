import unittest

from unittest.mock import patch
from aioresponses import aioresponses

from src.api.amoCRM.tags import TagsFetcher
from src.core.config import settings, logger


class TestTagsFetcher(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_new_tag(self, mocked):
        tag_name = "Test Tag"
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/tags/'
        post_response = {}
        mocked.post(url, status=200, payload=post_response)

        with patch.object(logger, 'info') as mock_info, patch.object(logger, 'error') as mock_error:
            await TagsFetcher.new_tag(tag_name)
            mock_info.assert_called_with(f'Тег {tag_name} создан')
            mock_error.assert_not_called()

    @aioresponses()
    async def test_get_tag_by_name(self, mocked):
        tag_name = "Test Tag"
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/tags/?filter[name]={tag_name}'
        get_response = {
            "_embedded": {
                "tags": [
                    {"id": 1, "name": "Test Tag"}
                ]
            }
        }
        mocked.get(url, payload=get_response)

        result = await TagsFetcher.get_tag_by_name(tag_name)
        self.assertEqual(result, [{'id': 1}])

    @aioresponses()
    async def test_get_old_lead_tags_ids(self, mocked):
        lead_id = "1"
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/{lead_id}'
        get_response = {
            "_embedded": {
                "tags": [
                    {"id": 1, "name": "Tag 1"},
                    {"id": 2, "name": "Tag 2"}
                ]
            }
        }
        mocked.get(url, payload=get_response)

        result = await TagsFetcher.get_old_lead_tags_ids(lead_id)
        expected = [{'id': 1}, {'id': 2}]
        self.assertEqual(result, expected)

    @aioresponses()
    async def test_add_new_tag(self, mocked):
        lead_id = "1"
        tag_name = "New Tag"
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/{lead_id}'

        old_tags_response = {
            "_embedded": {
                "tags": [
                    {"id": 1, "name": "Tag 1"}
                ]
            }
        }
        new_tag_response = {
            "_embedded": {
                "tags": [
                    {"id": 2, "name": "New Tag"}
                ]
            }
        }
        patch_response = {}

        with patch.object(TagsFetcher, 'get_old_lead_tags_ids', return_value=[{'id': 1}]), \
                patch.object(TagsFetcher, 'get_tag_by_name', return_value=[{'id': 2}]), \
                patch.object(logger, 'info') as mock_info, \
                patch.object(logger, 'error') as mock_error:
            mocked.patch(url, status=200, payload=patch_response)
            await TagsFetcher.add_new_tag(lead_id, tag_name)
            mock_info.assert_called_with(f'Тег {tag_name} добавлен к сделке {lead_id}')
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
