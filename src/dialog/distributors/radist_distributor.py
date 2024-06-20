from sqlalchemy.exc import IntegrityError

from src.core.config import logger

from src.dialog.objections.assistant import Assistant

from src.api.amoCRM.leads import LeadFetcher

from src.orm.crud.amo_leads import AmoLeadsCRUD
from src.orm.crud.amo_statuses import AmoStatusesCRUD
from src.orm.crud.radist_chats import ChatStepsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD


async def radist_data_processing(data):
    # Работаем только с входящими сообщениями, исходящие просто записываем в БД
    try:
        message_text = data['event']['message']['text']['text']
    except KeyError:
        message_text = ''
    if data['event']['message']['direction'] == 'inbound' and data['event']['message']['message_type'] == 'text':
        # Сохраняем входящее сообщение в БД
        chat_id = data['event']['chat_id']
        try:
            await RadistMessagesCRUD.save_new_message(data)
            # Получаем список всех неотвеченных сообщений
            new_messages = await RadistMessagesCRUD.get_all_unanswered_messages(chat_id)
        except IntegrityError:
            new_messages = None
        try:
            # Получаем необходимые данные по клиенту
            contact_id, lead_id, _ = await AmoLeadsCRUD.get_value_by_chat_id(
                chat_id, ['contact_id', 'lead_id', 'status_id']
            )
            # Получаем ID статуса "СТАРТ НЕЙРО"
            neuro_status_id = await AmoStatusesCRUD.get_neuro_status_id("СТАРТ НЕЙРО")
            status_id = await LeadFetcher.get_lead_status_id_by_lead_id(str(lead_id))
            # Сравниваем ID статуса "СТАРТ НЕЙРО" со статусом пользователя
            if status_id == neuro_status_id:
                logger.info(f"Получено входящее сообщение в сделке #{lead_id}: {message_text}")
                # Получаем текущий шаг ассистента
                step = await ChatStepsCRUD.get_step(chat_id)
                # В зависимости от этого шага распределяем его между ассистентами
                if step == 'survey':
                    await Assistant.get_survey_response_stream(
                        chat_id=chat_id,
                        lead_id=lead_id,
                        contact_id=contact_id,
                        new_messages=new_messages,
                    )
                else:
                    await Assistant.get_registration_response_stream(
                        chat_id=chat_id,
                        lead_id=lead_id,
                        contact_id=contact_id,
                        new_messages=new_messages,
                    )
        except TypeError:
            pass
    else:
        try:
            await RadistMessagesCRUD.save_new_message(data)
        except IntegrityError:
            pass
