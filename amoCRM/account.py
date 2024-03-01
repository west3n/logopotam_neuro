import asyncio
import aiohttp

from decouple import config

ACCESS_TOKEN = config('ACCESS_TOKEN')
SUBDOMAIN_URL = config('SUBDOMAIN_URL')


class AccountFetcher:
    def __init__(self, access_token: str, subdomain_url: str):
        """
        Инициализация объекта класса LeadFetcher.

        :param access_token: Строка, токен доступа для аутентификации
        :param subdomain_url: Строка, URL поддомена для API запросов
        """
        self.access_token = access_token
        self.subdomain_url = subdomain_url

    def get_headers(self):
        """
        Формирование заголовков запроса.

        :return: Словарь, содержащий заголовки запроса, включая авторизацию и тип контента
        """
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    async def get_account_info(self):
        """
        Получение информации об аккаунте
        :return:
        """
        url = self.subdomain_url + '/api/v4/account?with=amojo_id'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=self.get_headers()) as response:
                response_json = await response.json()
                print(response_json)


async def get_account_info():
    account_fetcher = AccountFetcher(ACCESS_TOKEN, SUBDOMAIN_URL)
    account_info = await account_fetcher.get_account_info()


if __name__ == '__main__':
    asyncio.run(get_account_info())

