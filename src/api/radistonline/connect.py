import asyncio

import aiohttp

from src.core.config import settings, headers


class RadistOnlineConnect:
    @staticmethod
    async def get_connection_id():
        """
        Получение ID подключения, необходим для работы с методами API
        :return: ID в формате целочисленного значения (int)
        """
        url = settings.RADIST_SUBDOMAIN_URL + 'connections/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.RADIST_HEADERS) as response:
                response_json = await response.json()
                return int(response_json['connections'][0]['id'])


if __name__ == '__main__':
    connection_id = asyncio.run(RadistOnlineConnect.get_connection_id())
    print(connection_id)