from src.dialog.objections.assistant import Assistant, RegistrationAssistant

from src.orm.crud.amo_leads import AmoLeadsCRUD
from src.orm.crud.amo_statuses import AmoStatusesCRUD
from src.orm.crud.radist_chats import ChatStepsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD


async def radist_data_processing(data):
    # Работаем только с входящими сообщениями, исходящие просто записываем в БД
    if data['event']['message']['direction'] == 'inbound':
        chat_id = data['event']['chat_id']
        messages_text = data['event']['message']['text']['text']
        message_id = data['event']['message']['message_id']
        try:
            # Получаем необходимые данные по клиенту
            contact_id, lead_id, status_id = await AmoLeadsCRUD.get_value_by_chat_id(
                chat_id, ['contact_id', 'lead_id', 'status_id']
            )
            # Получаем ID статуса "СТАРТ НЕЙРО"
            neuro_status_id = await AmoStatusesCRUD.get_neuro_status_id("СТАРТ НЕЙРО")
            # Сравниваем ID статуса "СТАРТ НЕЙРО" со статусом пользователя
            if status_id == neuro_status_id:
                # Первым делом нам нужно получить шаг алгоритма и жалобы от пользователя
                step = await ChatStepsCRUD.get_step(chat_id)
                # Если мы на шаге 2.0 или 3.1 в алгоритме, то добавляем последнее сообщение
                # от ассистента для более точного распознавания LLM-инструктором
                if step == 'survey':
                    await Assistant.get_response(
                        chat_id=chat_id,
                        lead_id=lead_id,
                        contact_id=contact_id,
                        user_prompt=messages_text
                    )
                else:
                    await RegistrationAssistant.get_response(
                        chat_id=chat_id,
                        lead_id=lead_id,
                        user_prompt=messages_text
                    )

        except TypeError:
            # Если данные не найдены, значит сообщение получено не от клиента, с которым мы общаемся
            pass
    else:
        # Сохраняем исходящее сообщение в БД
        await RadistMessagesCRUD.save_new_message(data)
