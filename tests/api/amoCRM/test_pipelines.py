import unittest

from aioresponses import aioresponses

from src.api.amoCRM.pipelines import PipelineFetcher
from src.core.config import settings


class TestPipelineFetcher(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_get_pipelines(self, mocked):
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/pipelines'
        pipelines_response = {
            "_embedded": {
                "pipelines": [
                    {"id": 1, "name": "Logopotam"},
                    {"id": 2, "name": "Not Logopotam"}
                ]
            }
        }
        mocked.get(url, payload=pipelines_response)

        result = await PipelineFetcher.get_pipelines()
        self.assertEqual(result, pipelines_response['_embedded']['pipelines'])

    @aioresponses()
    async def test_get_pipeline_statuses(self, mocked):
        pipeline_id = settings.LOGOPOTAM_PIPELINE_ID
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/pipelines/{pipeline_id}/statuses'
        statuses_response = {
            "_embedded": {
                "statuses": [
                    {"id": 1, "name": "СТАРТ НЕЙРО"},
                    {"id": 2, "name": "ТРЕБУЕТСЯ МЕНЕДЖЕР"}
                ]
            }
        }
        mocked.get(url, payload=statuses_response)

        result = await PipelineFetcher.get_pipeline_statuses()
        expected = {
            1: (pipeline_id, "СТАРТ НЕЙРО"),
            2: (pipeline_id, "ТРЕБУЕТСЯ МЕНЕДЖЕР")
        }
        self.assertEqual(result, expected)

    @aioresponses()
    async def test_get_pipeline_id_by_name(self, mocked):
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/leads/pipelines'
        pipelines_response = {
            "_embedded": {
                "pipelines": [
                    {"id": 1, "name": "Logopotam"},
                    {"id": 2, "name": "Not Logopotam"}
                ]
            }
        }
        mocked.get(url, payload=pipelines_response)

        result = await PipelineFetcher.get_pipeline_id_by_name("Logopotam")
        self.assertEqual(result, 1)

    @aioresponses()
    async def test_get_pipeline_status_id_by_name(self, mocked):
        pipeline_id = settings.LOGOPOTAM_PIPELINE_ID
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/pipelines/{pipeline_id}/statuses'
        statuses_response = {
            "_embedded": {
                "statuses": [
                    {"id": 1, "name": "СТАРТ НЕЙРО"},
                    {"id": 2, "name": "ТРЕБУЕТСЯ МЕНЕДЖЕР"}
                ]
            }
        }
        mocked.get(url, payload=statuses_response)

        result = await PipelineFetcher.get_pipeline_status_id_by_name("СТАРТ НЕЙРО")
        self.assertEqual(result, 1)

    @aioresponses()
    async def test_get_pipeline_status_name_by_id(self, mocked):
        pipeline_id = settings.LOGOPOTAM_PIPELINE_ID
        url = settings.AMO_SUBDOMAIN_URL + f'/api/v4/leads/pipelines/{pipeline_id}/statuses'
        statuses_response = {
            "_embedded": {
                "statuses": [
                    {"id": 1, "name": "СТАРТ НЕЙРО"},
                    {"id": 2, "name": "ТРЕБУЕТСЯ МЕНЕДЖЕР"}
                ]
            }
        }
        mocked.get(url, payload=statuses_response)

        result = await PipelineFetcher.get_pipeline_status_name_by_id(1)
        self.assertEqual(result, "СТАРТ НЕЙРО")


if __name__ == '__main__':
    unittest.main()
