import asyncio
import uuid
from datetime import datetime

from openai import BadRequestError

from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.api.amoCRM.leads import LeadFetcher
from src.api.radistonline.messages import RadistonlineMessages

from src.core.config import settings, openai_clients
from src.core.texts import AlgorythmContinuedTexts, SecondStepTexts, DialogFinishTexts

from src.dialog.objections.llm_instructor import SendImageChecker
from src.orm.crud.amo_contacts import AmoContactsCRUD

from src.orm.crud.radist_chats import RadistChatsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD

openai_client = openai_clients.OPENAI_ASYNC_CLIENT


class Assistant:
    @staticmethod
    async def create_thread():
        """
        Получаем новый ID треда для общения с ассистентом
        :return: ID треда
        """
        thread = await openai_client.beta.threads.create()
        return thread.id

    @staticmethod
    async def get_response(chat_id: int, user_prompt: str, step: str, lead_id: int, contact_id: int):
        """
        Здесь описана логика получения ответа от ассистента, в случае большого количества одновременных запросов,
        ассистент откладывает ответы в очередь и отвечает в порядке очереди, избегая возникновения ошибок

        :param contact_id: ID контакта
        :param lead_id: ID сделки
        :param step: Шаг в алгоритме, нужен для определения исходящего сообщения в зависимости от шага в диалоге
        :param chat_id: ID чата для сохранения нового Thread ID
        :param user_prompt: Текст сообщения от пользователя
        :return: new_message - сообщение от ассистента и thread_id - ID треда для записи в БД, если отсутствовал
        """
        # Получаем thread_id из БД пользователя, если отсутствует, создаём новый и сохраняем
        thread_id = await RadistChatsCRUD.get_thread_id(chat_id)
        if not thread_id:
            thread_id = await Assistant.create_thread()
            await RadistChatsCRUD.save_new_thread(chat_id, thread_id)
        while True:
            try:
                # Создаём новую задачу в указанном thread_id
                await openai_client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=user_prompt,
                )
                run = await openai_client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=settings.OPENAI_ASSISTANT_ID
                )
                # Раз в секунду проверяем статус
                while run.status != "completed":
                    await asyncio.sleep(1)
                    run = await openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                    if run.status in ["cancelling", "cancelled", "failed", "expired"]:
                        await openai_client.beta.threads.messages.create(
                            thread_id=thread_id,
                            role="user",
                            content=user_prompt,
                        )
                        run = await openai_client.beta.threads.runs.create(
                            thread_id=thread_id,
                            assistant_id=settings.OPENAI_ASSISTANT_ID
                        )
                messages = await openai_client.beta.threads.messages.list(thread_id=thread_id)
                response = messages.data[0].content[0].text.value
                if user_prompt == response:
                    continue
                else:
                    # Здесь мы дополнительно проверяем сообщение ассистента на предмет завершения диалога и
                    # необходимости прикрепить картинку к отправленному сообщению

                    send_image = await SendImageChecker.send_image(response)
                    is_dialog_finished = DialogFinishTexts.get_dialog_finish_status(response)
                    print("IS DIALOG FINISHED: ", is_dialog_finished)
                    print("SEND IMAGE: ", send_image)
                    if send_image:
                        await RadistonlineMessages.send_message(chat_id=chat_id, text=response)
                        await RadistonlineMessages.send_image(chat_id, settings.ONLINE_ADVANTAGES_IMAGE_URL)
                    if is_dialog_finished:
                        # Если диалог завершён на позитивной ноте, но алгоритм не завершён,
                        # необходимо отправить определённое сообщение в зависимости от шага алгоритма
                        if is_dialog_finished == 'positive' and step != "COMPLETED":
                            if step == '1.0':
                                survey_data = await CustomFieldsFetcher.get_survey_lead_fields(str(lead_id))
                                diagnosis = survey_data['Подробнее о запросе']
                                response = AlgorythmContinuedTexts.get_step_1_0_text(diagnosis)
                            elif step == '1.1':
                                unanswered_fields_2, _ = await AmoContactsCRUD.get_contact_values(contact_id)
                                response = AlgorythmContinuedTexts.get_step_1_1_text(unanswered_fields_2)
                            elif step == '2.0':
                                await RadistonlineMessages.send_message(
                                    chat_id=chat_id,
                                    text=SecondStepTexts.FIRST_MESSAGE_TEXT
                                )
                                response = SecondStepTexts.FIRST_MESSAGE_QUESTION_TEXT

                        # Если диалог с клиентом и основной алгоритм завершёны, то передаём сделку менеджеру
                        else:
                            await LeadFetcher.change_lead_status(lead_id, "ТРЕБУЕТСЯ МЕНЕДЖЕР")

                    # Отправляем сгенерированное сообщение и сохраняем его в БД
                    await RadistonlineMessages.send_message(chat_id=chat_id, text=response)
                    data = {
                        "event": {
                            "chat_id": chat_id,
                            "message": {
                                "message_id": str(uuid.uuid4()),
                                "direction": "outbound",
                                "created_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                                "text": {
                                    "text": response
                                }
                            },
                        }
                    }
                    await RadistMessagesCRUD.save_new_message(data)
                    break
            except BadRequestError:
                await asyncio.sleep(10)
