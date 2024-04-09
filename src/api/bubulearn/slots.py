import asyncio

import aiohttp

from src.core.config import settings, headers


class BubulearnSlotsFetcher:

    @staticmethod
    async def get_slots():
        """
        Запрос на получение слотов
        :return: Список слотов
        """
        url = settings.BUBULEARN_SUBDOMAIN_URL + 'slots/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.BUBULEARN_HEADERS) as response:
                data = await response.json()
                return data['slots']

    @staticmethod
    async def add_diagnostic(slot_id: str, request: str, lead_id: int, phone: str, student_name: str,
                             student_birthdate: str, customer_name: str = None):
        """
        Запись клиента на приём
        :param slot_id: ID слота
        :param request: Запрос клиента
        :param lead_id: id лида из AmoCRM
        :param phone: Номер телефона клиента
        :param student_name: Имя ребёнка
        :param student_birthdate: Дата рождения ребёнка
        :param customer_name: Имя клиента (необязательно)
        :return:
        """
        url = settings.BUBULEARN_SUBDOMAIN_URL + '/events/diagnostic/'
        data = {'slot_id': slot_id, 'request': request, 'lead_id': lead_id, 'phone_number': phone,
                'student_name': student_name, 'student_birthdate': student_birthdate}
        if customer_name:
            data['customer_name'] = customer_name
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.BUBULEARN_HEADERS, json=data) as response:
                return True if response.status == 200 else False


if __name__ == '__main__':
    slots = asyncio.run(BubulearnSlotsFetcher.get_slots())
    for slot in slots:
        print(slot)
