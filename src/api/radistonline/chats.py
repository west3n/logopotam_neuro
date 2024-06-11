import aiohttp

from src.core.config import settings, headers, logger
from src.api.radistonline.contacts import RadistOnlineContacts


class RadistOnlineChats:
    @staticmethod
    async def create_new_chat(name: str, phone: str):
        """
        Создание нового чата

        :param name: Имя пользователя
        :param phone: Номер телефона пользователя
        :return: ID созданного чата или None, если произошла ошибка
        """
        url = settings.RADIST_SUBDOMAIN_URL + "messaging/chats/"
        connection_id = settings.CONNECTION_ID
        contact_id = await RadistOnlineContacts.create_contact(name, phone)
        data = {
            "connection_id": connection_id,
            "contact_id": contact_id,
            "phone": phone,
            "user_name": name
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.RADIST_HEADERS, json=data) as response:
                response_json = await response.json()
                if response.status == 200:
                    logger.info(f"Чат с номером телефона {phone} успешно создан! ID: {response_json['chat_id']}")
                    return response_json['chat_id']
                else:
                    logger.error(f"Проблема при создании чата с номером телефона {phone}: {str(response_json)}")
                    return None
