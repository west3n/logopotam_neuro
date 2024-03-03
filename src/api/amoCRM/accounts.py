import aiohttp

from src.core.config import settings, headers


class AccountFetcher:
    @staticmethod
    async def get_account_info():
        """
        Получение информации об аккаунте
        :return:
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/account?with=amojo_id'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                return response_json
