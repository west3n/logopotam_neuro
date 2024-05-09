import asyncio
import aiohttp

from datetime import datetime

from src.core.config import settings, headers


def normalize_date(date: str):
    # Преобразование даты в удобный для ассистента формат
    new_datetime = (datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ'))
    day_of_week = new_datetime.strftime("%A")
    weekday = {
        'Monday': 'Понедельник',
        'Tuesday': 'Вторник',
        'Wednesday': 'Среда',
        'Thursday': 'Четверг',
        'Friday': 'Пятница',
        'Saturday': 'Суббота',
        'Sunday': 'Воскресенье'
    }
    return new_datetime, weekday[day_of_week]


class BubulearnSlotsFetcher:
    @staticmethod
    async def get_slots(slot_id: str = None):
        """
        Запрос на получение слотов
        :return: Список слотов в строковой форме для ассистента
        """
        url = settings.BUBULEARN_SUBDOMAIN_URL + 'slots/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.BUBULEARN_HEADERS) as response:
                data = await response.json()
                slots = []
                for slot in data['slots']:
                    db_slot = {
                            'slot_id': slot['slot_id'],
                            'weekday': normalize_date(slot['start'])[1],
                            'start_time': normalize_date(slot['start'])[0]
                    }
                    slots.append(db_slot)
                if slot_id:
                    return next(
                        (
                            f'{slot_["start_time"].strftime("%d.%m.%Y %H:%M")} ({slot_["weekday"]})'
                            for slot_ in slots if slot_['slot_id'] == slot_id
                        ), None
                    )
                return slots

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
