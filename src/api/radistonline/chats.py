import aiohttp

from src.core.config import settings, headers
from src.api.radistonline.connect import RadistOnlineConnect


class RadistonlineChats:
    @staticmethod
    async def get_all_chats():
        """
        Получение всех чатов
        :return: Список всех чатов, каждый чат в формате JSON
        """
        url = settings.RADIST_SUBDOMAIN_URL + 'messaging/chats/with_contacts/'
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, headers=headers.RADIST_HEADERS) as response:
                response_json = await response.json()
                return response_json["data"]

    @staticmethod
    async def create_new_chat(contact_id: int, name: str, phone: str):
        """
        Создание нового чата

        :param contact_id: ID контакта, с которым необходимо начать чат
        :param name: Имя пользователя, с которым необходимо начать чат
        :param phone: Номер телефона пользователя, с которым необходимо начать чат
        :return: Текст с успешным созданием чата и его ID или текст и код ошибки
        """
        url = settings.RADIST_SUBDOMAIN_URL + "messaging/chats/"
        connection_id = await RadistOnlineConnect.get_connection_id()
        data = {
            "connection_id": connection_id,
            "contact_id": contact_id,
            "phone": phone,
            "user_name": name
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.RADIST_HEADERS, json=data) as response:
                if response.status == 200:
                    response_json = await response.json()
                    return "Чат успешно создан!", response_json['chat_id']
                else:
                    return "Возникла проблема при создании чата!" + await response.text(), None
