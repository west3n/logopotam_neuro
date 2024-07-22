import unittest

from aioresponses import aioresponses

from src.api.radistonline.connect import RadistOnlineConnect
from src.core.config import settings


class TestRadistOnlineConnect(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_get_connection_id(self, mocked):
        url = settings.RADIST_SUBDOMAIN_URL + '/connections/'
        get_response = {"connections": "12345"}

        mocked.get(url, payload=get_response)

        result = await RadistOnlineConnect.get_connection_id()
        self.assertEqual(result, "12345")


if __name__ == '__main__':
    unittest.main()
