import asyncio
import uuid
from datetime import datetime

from src.api.radistonline.messages import RadistonlineMessages
from src.core.config import logger
from src.core.texts import SecondStepTexts

from src.dialog.objections.llm_instructor import ObjectionsChecker
from src.dialog.objections.assistant import Assistant
from src.dialog.steps.first.handlers import step_1_0_handler, step_1_1_handler
from src.dialog.steps.second.handlers import step_2_0_handler

from src.orm.crud.amo_leads import AmoLeadsCRUD
from src.orm.crud.radist_chats import ChatStepsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD


async def radist_data_processing(data):
    # Работаем только с входящими сообщениями, исходящие просто записываем в БД
    if data['event']['message']['direction'] == 'inbound':
        chat_id = data['event']['chat_id']
        messages_text = data['event']['message']['text']['text']
        message_id = data['event']['message']['message_id']
        try:
            contact_id, lead_id = await AmoLeadsCRUD.get_value_by_chat_id(chat_id, ['contact_id', 'lead_id'])
            is_objection, category = await ObjectionsChecker.check_message_for_objection(messages_text)
            print(is_objection, category)
            if is_objection:
                response = await Assistant.get_response(chat_id, messages_text)
                await RadistonlineMessages.send_message(chat_id=chat_id, text=response)
            else:
                # Проверяем, находится ли пользователь на каком-то шаге
                step = await ChatStepsCRUD.read(chat_id=chat_id)
                if step:
                    # В шаге 1.1 логика немного отличается
                    if step == '1.1':
                        len_messages = await RadistMessagesCRUD.save_new_message(data)
                        await asyncio.sleep(5 + 5 * len_messages)

                        # Теперь нам нужно получить ID и текст всех неотвеченных сообщений из этого чата
                        all_unanswered_messages = await RadistMessagesCRUD.get_all_unanswered_messages(chat_id)
                        if all_unanswered_messages:
                            messages_ids = [message[0] for message in all_unanswered_messages]
                            messages_text = '\n'.join([message[1] for message in all_unanswered_messages])
                            print(f"Все неотвеченные сообщения: {messages_text}")

                            # Меняем статус у всех сообщений на processing, чтобы их не использовать в других процессах
                            for message_id in messages_ids:
                                await RadistMessagesCRUD.change_status(message_id, 'processing')
                            await step_1_1_handler(messages_text, contact_id, chat_id, lead_id)

                            # Меняем статус у всех сообщений на answered
                            for message_id in messages_ids:
                                await RadistMessagesCRUD.change_status(message_id, 'answered')

                    # В остальных шагах логика одинаковая
                    handlers = {
                        '1.0': step_1_0_handler,
                        '2.0': step_2_0_handler
                    }

                    if step in handlers:
                        await RadistMessagesCRUD.change_status(message_id, 'processing')
                        await handlers[step](messages_text, chat_id, lead_id)
                        await RadistMessagesCRUD.change_status(message_id, 'answered')
        except TypeError:
            # Если данные не найдены, значит сообщение получено не от клиента, с которым мы общаемся
            pass
    else:
        await RadistMessagesCRUD.save_new_message(data)
