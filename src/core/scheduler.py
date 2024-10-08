import asyncio

from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.tags import TagsFetcher
from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.api.radistonline.messages import RadistonlineMessages

from src.core.config import logger
from src.core.texts import SchedulerTexts
from src.orm.crud.amo_leads import AmoLeadsCRUD

from src.orm.crud.amo_statuses import AmoStatusesCRUD
from src.orm.crud.radist_chats import RadistChatsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD

from aiohttp.client_exceptions import ContentTypeError


async def send_10_min_delay_messages():
    """
    Отправляет сообщения после 10-минутного молчания
    :return: None
    """
    chats = await RadistMessagesCRUD.get_10_minutes_delay_chats()
    neuro_status_id = await AmoStatusesCRUD.get_neuro_status_id("СТАРТ НЕЙРО")

    semaphore = asyncio.Semaphore(2)

    async def process_chat(lead_id, chat_id, step):
        async with semaphore:
            try:
                amo_status = await LeadFetcher.get_lead_status_id_by_lead_id(str(lead_id))
                if amo_status and neuro_status_id == amo_status:
                    await RadistChatsCRUD.change_delay_status(int(chat_id), True)
                    survey_text = SchedulerTexts.SURVEY_10MIN_DELAY
                    slots_text = SchedulerTexts.SLOTS_10MIN_DELAY
                    message_text = survey_text if step == 'survey' else slots_text
                    await RadistonlineMessages.send_obvious_message(int(lead_id), int(chat_id), message_text)
                    logger.info(f"Отправлено сообщение после 10-минутного молчания (ID сделки: {lead_id}): {message_text}")
            except ContentTypeError:
                logger.error(f"Не удалось получить статус сделки с ID {lead_id} (10-минутное молчание)")
            except Exception as e:
                logger.error(f"Ошибка при обработке чата {chat_id} для лида {lead_id}: {e}")

    await asyncio.gather(*(process_chat(lead_id, chat_id, step) for lead_id, chat_id, step in chats))


async def change_status_15_min_delay_messages():
    """
    Изменяет статус сделки после 15-минутного молчания
    :return: None
    """
    chats = await RadistMessagesCRUD.get_15_minutes_delay_chats()
    neuro_status_id = await AmoStatusesCRUD.get_neuro_status_id("СТАРТ НЕЙРО")

    semaphore = asyncio.Semaphore(2)

    async def process_chat(lead_id, chat_id, step):
        async with semaphore:
            try:
                amo_status = await LeadFetcher.get_lead_status_id_by_lead_id(str(lead_id))
                if neuro_status_id == amo_status:
                    await LeadFetcher.change_lead_status(int(lead_id), 'В работе ( не было звонка)')
                    await CustomFieldsFetcher.change_status(int(lead_id), text="Не ответил на два сообщения от НМ")
                    await AmoLeadsCRUD.delete_lead_and_related_data(int(lead_id))
                    if step == 'registration':
                        await TagsFetcher.add_new_tag(str(lead_id), 'не было нужного слота')
                    logger.info(f"Изменён статус сделки #{lead_id} после 15-минутного молчания")
            except ContentTypeError:
                logger.error(f"Не удалось получить статус сделки #{lead_id} (15-минутное молчание)")
            except Exception as e:
                logger.error(f"Ошибка при обработке чата {chat_id} для лида {lead_id}: {e}")

    await asyncio.gather(*(process_chat(lead_id, chat_id, step) for lead_id, chat_id, step in chats))
