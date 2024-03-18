import asyncio

from src.core.config import logger
from src.dialog.steps.first.handlers import first_step_handler
from src.dialog.steps.second.handlers import second_step_handler, second_one_step_handler
from src.dialog.steps.third.handlers import third_step_handler
from src.orm.crud.amo_leads import AmoLeadsCRUD
from src.orm.crud.amo_statuses import AmoStatusesCRUD
from src.orm.crud.chat_steps import ChatStepsCRUD
from src.orm.crud.radist_chats import RadistChatsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD


async def radist_data_processing(data):
    """
    В этой функции выстраивается вся логика обработки входящего сообщения WhatsApp и отправка ответа пользователю

    :param data: JSON с данными о входящем сообщении
    """
    # Отлавливаем только входящие и исходящие сообщения
    try:
        if not data['event']['message']['text']['text'] == 'test':
            chat_id = data['event']['chat_id']
            contact_id = await AmoLeadsCRUD.get_value_by_chat_id(chat_id, 'contact_id')
            lead_id = await AmoLeadsCRUD.get_value_by_chat_id(chat_id, 'lead_id')
            print(chat_id, contact_id, lead_id)

            # Проверяем, есть ли данный чат в списке чатов в БД. Если чата нет, значит мы словили постороннее сообщение
            chat_exist = await RadistChatsCRUD.chat_existence(chat_id)
            if chat_exist:
                print(f"Чат с ID {chat_id} существует, идём дальше")

                # Необходимо проверить статус сделки в amoСRM. Если статус не "Старт Нейро", то сообщение пропускаем
                start_neuro_status_id = await AmoStatusesCRUD.get_id_status_by_name("Старт Нейро")
                try:
                    lead_status = await AmoLeadsCRUD.get_value_by_chat_id(chat_id, 'status_id')
                except TypeError:
                    await asyncio.sleep(30)
                    lead_status = await AmoLeadsCRUD.get_value_by_chat_id(chat_id, 'status_id')
                if lead_status == start_neuro_status_id:
                    print("Статус в amoCRM подходящий, идём дальше")

                    # Сохраняем сообщение в БД и получаем количество неотвеченных сообщений для прогрессивной шкалы
                    len_messages = await RadistMessagesCRUD.save_new_message(data)

                    # Затем проверяем, что отловленное сообщения является входящим
                    if data['event']['message']['direction'] == 'inbound':
                        print("Ожидайте 2 минуты...")
                        """Здесь мы должны сделать поведение нейроменеджера похожим на поведение человека, для этого нам 
                        необходимо подождать 2 минуты для того, чтобы не отвечать на каждое сообщения от пользователя, 
                        которые он отправляет один за другим, чтобы потом собрать их воедино и ответить разом.
                        Если за 2 минуты не придёт больше одного сообщения, то он ответит только на одно, если их будет 
                        больше, то ответит на все неотвеченные одним сообщением, сменит их статусы и не будет на них 
                        отвечать повторно."""

                        # Здесь у нас прогрессивная шкала sleep в зависимости от непрочитанных сообщений
                        await asyncio.sleep(5 + 2 * len_messages)
                        # await asyncio.sleep(90 + 30 * len_messages)

                        # Теперь нам нужно получить ID и текст всех неотвеченных сообщений из этого чата
                        all_unanswered_messages = await RadistMessagesCRUD.get_all_unanswered_messages(chat_id)
                        if all_unanswered_messages:
                            messages_ids = [message[0] for message in all_unanswered_messages]
                            messages_text = '\n'.join([message[1] for message in all_unanswered_messages])
                            print(f"Все неотвеченные сообщения: {messages_text}")

                            # Меняем статус у всех сообщений на processing, чтобы их не использовать в других процессах
                            for message_id in messages_ids:
                                await RadistMessagesCRUD.change_status(message_id, 'processing')

                            # Выясняем, на каком шаге диалога сейчас находится клиент и в зависимости от этого
                            # распределяем текст к определённому инструктору
                            step = await ChatStepsCRUD.read(lead_id)
                            if step == '1.1':
                                await first_step_handler(messages_text, contact_id, chat_id, lead_id)

                            if step == '2.0':
                                await second_step_handler(messages_text, chat_id, lead_id)

                            if step == "2.1":
                                await second_one_step_handler(messages_text, chat_id, lead_id)

                            if step == "3.0":
                                await third_step_handler(messages_text, chat_id, lead_id)

                            for message_id in messages_ids:
                                await RadistMessagesCRUD.change_status(message_id, 'answered')

                        else:
                            # Если у нас нет неотвеченных сообщений, значит они уже используются в других местах
                            logger.info(f"Неотвеченных сообщений в ID чата {chat_id} не найдено, шаг пропускается")
                            print(f"Неотвеченных сообщений в ID чата {chat_id} не найдено, шаг пропускается")
                    else:
                        # Если это исходящее сообщение, то кроме записи в БД ничего не нужно
                        print(f"Записали исходящее сообщение в бд в чате {chat_id}")
                        logger.info(f"Записали исходящее сообщение в бд в чате {chat_id}")
                else:
                    print(f"У сделки с ID чата {chat_id} статус не соответствует необходимому для ответа")
                    logger.info(f"У сделки с ID чата {chat_id} статус не соответствует необходимому для ответа")
            else:
                print(f"Чата с ID {chat_id} не существует в БД, это сообщение необходимо пропустить")
                logger.info(f"Чата с ID {chat_id} не существует в БД, это сообщение необходимо пропустить")

    except KeyError:
        # Здесь обработка изменения статусов сообщений
        print(data)
