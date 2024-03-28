import asyncio

from src.api.amoCRM.leads import LeadFetcher
from src.api.radistonline.messages import RadistonlineMessages
from src.core.config import logger, settings
from src.core.texts import ComplainTypeTexts

from src.dialog.objections.llm_instructor import MessageCategoryChecker, DialogFinishChecker
from src.dialog.objections.assistant import Assistant
from src.dialog.steps.first.handlers import step_1_0_handler, step_1_1_handler
from src.dialog.steps.second.handlers import step_2_0_handler

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
            # Получаем данные по клиенту и получаем категорию сообщения и категорию жалобы, если она есть в тексте
            contact_id, lead_id, status_id = await AmoLeadsCRUD.get_value_by_chat_id(
                chat_id, ['contact_id', 'lead_id', 'status_id']
            )

            # Получаем ID статуса "СТАРТ НЕЙРО" и текст последнего сообщения от ассистента в чате
            start_neuro_status_id, robot_message_text = await AmoStatusesCRUD.get_status_id_and_last_robot_message(
                "СТАРТ НЕЙРО", chat_id
            )
            if status_id == start_neuro_status_id:
                # Первым делом нам нужно получить шаг алгоритма и жалобы от пользователя
                step, complain_step = await ChatStepsCRUD.get_step_and_complain_step(chat_id)
                # Если мы на втором шаге в алгоритме, то добавляем последнее сообщение
                # от ассистента для более точного распознавания LLM-инструктором
                messages_text = robot_message_text + "\n" + messages_text if step == '2.0' else messages_text
                print(messages_text)
                # Проверяем категорию сообщения для распределения задачи ассистенту
                algorythm, assistant, complain = await MessageCategoryChecker.check_message_for_objection(messages_text)
                print(algorythm, assistant, complain)
                # Если в тексте сообщения есть одна из категорий алгоритма, то задача распределяется в алгоритм
                if algorythm and algorythm in ['name', 'city', 'birthday', 'problem', 'diagnosis', 'zoom']:
                    if step == '1.1':
                        len_messages = await RadistMessagesCRUD.save_new_message(data)
                        await asyncio.sleep(15 * len_messages)

                        # Теперь нам нужно получить ID и текст всех неотвеченных сообщений из этого чата
                        all_unanswered_messages = await RadistMessagesCRUD.get_all_unanswered_messages(chat_id)
                        if all_unanswered_messages:
                            messages_ids = [message[0] for message in all_unanswered_messages]
                            messages_text = '\n'.join([message[1] for message in all_unanswered_messages])
                            print(f"Все неотвеченные сообщения: {messages_text}")

                            # Меняем статус у всех сообщений на processing, чтобы не использовать их в других процессах
                            for message_id in messages_ids:
                                await RadistMessagesCRUD.change_status(message_id, 'processing')
                            await step_1_1_handler(messages_text, contact_id, chat_id, lead_id)

                            # Меняем статус у всех сообщений на answered после завершения процесса
                            for message_id in messages_ids:
                                await RadistMessagesCRUD.change_status(message_id, 'answered')

                    # В остальных шагах логика одинаковая
                    handlers = {
                        '1.0': step_1_0_handler,
                        '2.0': step_2_0_handler
                    }

                    if step in handlers:
                        # Меняем статус у всех сообщений на processing, чтобы не использовать их в других процессах
                        await RadistMessagesCRUD.change_status(message_id, 'processing')
                        await handlers[step](messages_text, chat_id, lead_id)

                        # Меняем статус у всех сообщений на answered после завершения процесса
                        await RadistMessagesCRUD.change_status(message_id, 'answered')
                else:
                    # Если текст сообщения не относится к общему алгоритму, то мы проверяем, жалоба это или вопрос
                    if complain and not complain_step and complain != complain_step:
                        print(complain)
                        print(complain_step)
                        complain_first_message = {
                            'online': ComplainTypeTexts.ONLINE,
                            'expensive': ComplainTypeTexts.EXPENSIVE,
                            'decline': ComplainTypeTexts.DECLINE
                        }
                        await RadistonlineMessages.send_message(chat_id, text=complain_first_message[complain])
                        await ChatStepsCRUD.update(chat_id=chat_id, complain_step=complain)
                    else:
                        response = await Assistant.get_response(chat_id, messages_text)
                        await RadistonlineMessages.send_message(chat_id=chat_id, text=response)
                        is_dialog_finished, send_image = await DialogFinishChecker.check_dialog_finish(response)
                        if send_image:
                            await RadistonlineMessages.send_image(chat_id, settings.ONLINE_ADVANTAGES_IMAGE_URL)
                        if is_dialog_finished:
                            await LeadFetcher.change_lead_status(
                                lead_id, "ТРЕБУЕТСЯ МЕНЕДЖЕР"
                            )
                    #
                    # await RadistMessagesCRUD.save_new_message(data)
                    # await LeadFetcher.change_lead_status(
                    #     lead_id, "ТРЕБУЕТСЯ МЕНЕДЖЕР"
        except TypeError:
            # Если данные не найдены, значит сообщение получено не от клиента, с которым мы общаемся
            pass
    else:
        await RadistMessagesCRUD.save_new_message(data)
