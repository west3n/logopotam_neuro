import aiohttp

from src.core.config import settings, headers
from src.api.radistonline.contacts import RadistOnlineContacts


class RadistOnlineChats:

    @staticmethod
    async def create_new_chat(name: str, phone: str):
        """
        Создание нового чата

        :param name: Имя пользователя
        :param phone: Номер телефона пользователя
        :return: Текст с успешным созданием чата и его ID или текст и код ошибки
        """
        url = settings.RADIST_SUBDOMAIN_URL + "messaging/chats/"
        connection_id = settings.CONNECTION_ID
        _, contact_id = await RadistOnlineContacts.create_contact(name, phone)
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
