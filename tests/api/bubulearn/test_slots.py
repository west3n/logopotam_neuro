import unittest

from unittest.mock import patch
from aioresponses import aioresponses
from datetime import datetime

from src.api.bubulearn.slots import BubulearnSlotsFetcher
from src.core.config import settings, logger


class TestBubulearnSlotsFetcher(unittest.IsolatedAsyncioTestCase):

    @aioresponses()
    async def test_get_slots(self, mocked):
        url = settings.BUBULEARN_SUBDOMAIN_URL + 'slots/'
        get_response = {
            "slots": [
                {"slot_id": "1", "start": "2024-07-22T09:00:00Z"},
                {"slot_id": "2", "start": "2024-07-23T10:00:00Z"}
            ]
        }

        mocked.get(url, payload=get_response)

        with patch('src.api.bubulearn.slots.normalize_date') as mock_normalize_date:
            mock_normalize_date.side_effect = [
                (datetime(2024, 7, 22, 9, 0), "Понедельник"),
                (datetime(2024, 7, 22, 9, 0), "Понедельник"),
                (datetime(2024, 7, 23, 10, 0), "Вторник"),
                (datetime(2024, 7, 23, 10, 0), "Вторник")
            ]

            result = await BubulearnSlotsFetcher.get_slots()
            expected = [
                {'slot_id': '1', 'weekday': 'Понедельник', 'start_time': datetime(2024, 7, 22, 9, 0)},
                {'slot_id': '2', 'weekday': 'Вторник', 'start_time': datetime(2024, 7, 23, 10, 0)}
            ]
            self.assertEqual(result, expected)

    @aioresponses()
    async def test_is_slot_free(self, mocked):
        slot_id = "1"
        url = settings.BUBULEARN_SUBDOMAIN_URL + f'/slots/{slot_id}/free/'
        get_response = {"is_free": True}

        mocked.get(url, payload=get_response)

        with patch.object(logger, 'error') as mock_error:
            result = await BubulearnSlotsFetcher.is_slot_free(slot_id)
            self.assertTrue(result)
            mock_error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
