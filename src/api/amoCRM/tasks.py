import aiohttp
import datetime

from typing import Optional
from src.core.config import settings, headers


class TasksFetcher:
    @staticmethod
    async def get_all_tasks():
        """
        Получение информации обо всех задачах.

        :return: Список словарей, содержащий информацию о каждой задаче
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/tasks'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.AMO_HEADERS) as response:
                response_json = await response.json()
                return response_json['_embedded']['tasks']

    @staticmethod
    async def add_new_task(entity_id: int, task_type_id: int, task_text: str, complete_till: datetime.datetime):
        """
        Добавление новой задачи.

        :param entity_id: ID сущности, будь то сделка или контакт.
        :param task_type_id: Отправьте 1 для задачи "Связаться" или 2 для "Встреча".
        :param task_text: Текст описания задачи
        :param complete_till: Время выполнения задачи, формат должен быть datetime
        :return: Строка, сообщение об успешном или неудачном добавлении задачи
        """
        if task_type_id not in [1, 2]:
            return "Отправьте 1 для задачи 'Связаться' или 2 для 'Встреча'."
        if not isinstance(complete_till, datetime.datetime):
            return "Ошибка: complete_till должен быть объектом datetime."
        timestamp = int(complete_till.timestamp())
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/tasks'
        data = [
            {
                "task_type_id": task_type_id,
                "text": task_text,
                "complete_till": timestamp,
                "entity_type": "leads",
                "entity_id": entity_id
            }
        ]
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                if response.status == 200:
                    return "Задача успешно поставлена!"
                else:
                    return "Возникла ошибка при постановке задачи\n" + str(await response.text())

    @staticmethod
    async def change_task_type(
            task_id: int, new_task_type: Optional[int], new_task_text: str,
            complete_till: datetime.datetime
    ):
        """
        Изменение задачи.

        :param task_id: ID задачи, которую необходимо изменить. Обязательный параметр
        :param new_task_text: Новый текст задачи, обязательный параметр
        :param new_task_type: Новый тип задачи, передавайте None, чтобы не изменять параметр
        :param complete_till: Новое время выполнения задачи, обязательный параметр
        :return: Строка, сообщение об успешном или неудачном изменении задачи
        """
        url = settings.AMO_SUBDOMAIN_URL + '/api/v4/tasks/' + str(task_id)
        if not isinstance(complete_till, datetime.datetime):
            return "Ошибка: complete_till должен быть объектом datetime."
        timestamp = int(complete_till.timestamp())
        data = {
            "text": new_task_text,
            "task_type_id": new_task_type,
            "complete_till": timestamp
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url=url, headers=headers.AMO_HEADERS, json=data) as response:
                if response.status == 200:
                    return "Задача успешно изменена!"
                else:
                    return "Возникла ошибка при изменении задачи\n" + str(await response.text())
