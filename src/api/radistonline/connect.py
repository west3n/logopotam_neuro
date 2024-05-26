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
        url = 'https://api.radist.online/v2/companies/151429/connections/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.RADIST_HEADERS) as response:
                response_json = await response.json()
                return response_json['connections']


if __name__ == '__main__':
    connections = asyncio.run(RadistOnlineConnect.get_connection_id())
    for connection in connections:
        print(connection)