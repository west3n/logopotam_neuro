import aiohttp

from src.api.amoCRM.leads import LeadFetcher
from src.core.config import settings, headers, logger
from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.orm.crud.amo_leads import AmoLeadsCRUD
from src.orm.crud.amo_statuses import AmoStatusesCRUD


class RadistonlineMessages:
    @staticmethod
    async def send_message(chat_id: int, text: str):
        """
        Отправка сообщения через chat_id клиента

        :param chat_id: ID чата клиента из списка чатов Radist.Online
        :param text: Текст сообщения
        :return: Текст, сообщающий об успешной отправке сообщения (или кода с текстом ошибки)
        """
        lead_id = await AmoLeadsCRUD.get_value_by_chat_id(chat_id, 'lead_id')
        if lead_id:
            status_id = await LeadFetcher.get_lead_status_id_by_lead_id(str(lead_id))

            # Если статус сделки СТАРТ НЕЙРО
            if status_id == 66505833:
                url = settings.RADIST_SUBDOMAIN_URL + 'messaging/messages/'
                connection_id = settings.CONNECTION_ID
                data = {
                    "connection_id": connection_id,
                    "chat_id": chat_id,
                    "mode": "async",
                    "message_type": "text",
                    "text": {
                        "text": text
                    }
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(url=url, headers=headers.RADIST_HEADERS, json=data) as response:
                        response_json = await response.json()
                        if response.status == 200:
                            await CustomFieldsFetcher.message_counter(lead_id)
                        else:
                            logger.error(
                                f"Ошибка при отправке сообщения в сделке #{lead_id}: {str(response_json)}")
            else:
                logger.info(f"Не отправляем сообщение в сделке #{lead_id} потому что статус сделки не СТАРТ НЕЙРО")
        else:
            logger.info(f"Не отправляем сообщение потому что нет ID сделки для чата #{chat_id}")

    @staticmethod
    async def send_image(chat_id: int, image_url: str):
        """
        Отправка картинки через chat_id клиента

        :param chat_id: ID чата клиента из списка чатов Radist.Online
        :param image_url: URL картинки, который берётся через метод upload_file
        :return: None
        """
        url = settings.RADIST_SUBDOMAIN_URL + 'messaging/messages/'
        connection_id = settings.CONNECTION_ID
        data = {
            "connection_id": connection_id,
            "chat_id": chat_id,
            "mode": "async",
            "message_type": "image",
            "image": {
                "caption": '',
                "url": image_url
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.RADIST_HEADERS, json=data) as response:
                if response.status == 200:
                    logger.info(f"Картинка успешно отправлена! Чат #{chat_id}")
                else:
                    logger.error(f"Ошибка при отправке картинки в чат #{chat_id}! {str(response)}")
