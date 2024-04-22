import asyncio
import uuid
import pytz

from datetime import datetime

from openai import BadRequestError

from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.api.amoCRM.leads import LeadFetcher
from src.api.radistonline.messages import RadistonlineMessages
from src.api.bubulearn.slots import BubulearnSlotsFetcher

from src.core.config import settings, openai_clients, logger
from src.core.texts import ThirdStepsTexts

from src.dialog.objections.llm_instructor import (
    SendImageChecker, JSONChecker, SendZoomImageChecker, SurveyInitialCheck, GetSlotId
)
from src.orm.crud.amo_contacts import AmoContactsCRUD

from src.orm.crud.radist_chats import RadistChatsCRUD, ChatStepsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD

openai_client = openai_clients.OPENAI_ASYNC_CLIENT
current_day_of_week = {
    0: "понедельник",
    1: "вторник",
    2: "среда",
    3: "четверг",
    4: "пятница",
    5: "суббота",
    6: "воскресенье"
}


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
    async def get_response(chat_id: int, lead_id: int, contact_id: int, user_prompt: str):
        """
        Здесь описана логика получения ответа от ассистента, в случае большого количества одновременных запросов,
        ассистент откладывает ответы в очередь и отвечает в порядке очереди, избегая возникновения ошибок

        :param contact_id: ID контакта
        :param lead_id: ID сделки
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
                print("RESPONSE: ", response)
                if user_prompt == response:
                    continue
                else:
                    # Проверяем, является ли сообщение JSON
                    is_json = await JSONChecker.check_json(response)
                    print("JSON: ", is_json)
                    if is_json:
                        baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(
                            is_json)

                        # Возраст ребёнка мы высчитываем в количестве месяцев для более надёжной проверки.
                        if baby_age_month < 42 or segment == "C" or not for_online:

                            # Если сделка не прошла проверку, то просто меняем статус
                            await LeadFetcher.change_lead_status(
                                lead_id=lead_id,
                                status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР'
                            )
                            logger.info(f"Изменили статус задачи с ID {lead_id} на Требуется менеджер, "
                                        f"так как сделка не прошла первичную проверку")
                        else:
                            await RegistrationAssistant.get_response(chat_id=chat_id, lead_id=lead_id)
                            await ChatStepsCRUD.update(chat_id=chat_id, step="registration")
                            try:
                                child_info = {
                                    "city": is_json["Страна/город"],
                                    "child_name": is_json["Имя ребёнка"],
                                    "child_birth_date": is_json["Дата рождения"],
                                    "doctor_enquiry": is_json["Подробнее о запросе"],
                                    "diagnosis": is_json['Диагноз (если есть)'],
                                    "segment": segment,
                                }
                            except KeyError:
                                child_info = {
                                    "city": is_json["Страна/город"],
                                    "child_name": is_json["Имя ребенка"],
                                    "child_birth_date": datetime.strptime(is_json["Дата рождения"], "%Y-%m-%d"),
                                    "doctor_enquiry": is_json["Подробнее о запросе"],
                                    "diagnosis": is_json['Диагноз (если есть)'],
                                    "segment": segment,
                                }
                            await AmoContactsCRUD.update_contact_values(contact_id=contact_id,
                                                                        update_columns=child_info)
                            _, child_data = await AmoContactsCRUD.get_contact_values(contact_id)
                            await CustomFieldsFetcher.save_survey_lead_fields(lead_id, child_data)
                    else:
                        await RadistonlineMessages.send_message(chat_id=chat_id, text=response)
                        # Здесь мы дополнительно проверяем сообщение ассистента на предмет необходимости
                        # прикрепить картинку к отправленному сообщению
                        send_image = await SendImageChecker.send_image(response)
                        if send_image:
                            print("SEND IMAGE: ", send_image)
                            await RadistonlineMessages.send_image(chat_id, settings.ONLINE_ADVANTAGES_IMAGE_URL)
                    break
            except BadRequestError:
                await asyncio.sleep(10)


class RegistrationAssistant:
    """
    Это ассистент, который помогает записывать клиента на указанное время к специалисту
    """

    @staticmethod
    async def create_thread():
        """
        Получаем новый ID треда для общения с ассистентом
        :return: ID треда
        """
        thread = await openai_client.beta.threads.create()
        return thread.id

    @staticmethod
    async def get_response(chat_id: int, lead_id: int, user_prompt: str = None):
        """
        Здесь описана логика получения ответа от ассистента, в случае большого количества одновременных запросов,
        ассистент откладывает ответы в очередь и отвечает в порядке очереди, избегая возникновения ошибок

        :param lead_id: ID сделки
        :param chat_id: ID чата для сохранения нового Thread ID
        :param user_prompt: Текст сообщения от пользователя
        :return: new_message - сообщение от ассистента и thread_id - ID треда для записи в БД, если отсутствовал
        """
        # Получаем thread_id из БД пользователя, если отсутствует, создаём новый и сохраняем
        thread_id = await RadistChatsCRUD.get_registration_thread_id(chat_id)
        # Если нет текста сообщения, значит оно первое и должно быть списком с временем свободных слотов
        if not user_prompt:
            slots = await BubulearnSlotsFetcher.get_slots()
            moscow_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M')
            weekday = current_day_of_week[datetime.now(pytz.timezone('Europe/Moscow')).weekday()]
            user_prompt = "Cлоты на ближайшее время: " + slots + f"\n\nСейчас в Москве {moscow_time}, {weekday}"
        if not thread_id:
            thread_id = await RegistrationAssistant.create_thread()
            await RadistChatsCRUD.save_new_registration_thread_id(chat_id, thread_id)
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
                    assistant_id=settings.OPENAI_REGISTRATION_ASSISTANT_ID
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
                            assistant_id=settings.OPENAI_REGISTRATION_ASSISTANT_ID
                        )
                messages = await openai_client.beta.threads.messages.list(thread_id=thread_id)
                response = messages.data[0].content[0].text.value
                if user_prompt == response:
                    continue
                else:
                    if "True" in response:
                        # Здесь логика после успешного выбора времени
                        slot_id = await GetSlotId.get_slot_id(response)
                        time = await BubulearnSlotsFetcher.get_slots(slot_id=slot_id)
                        first_message, second_message = ThirdStepsTexts.approve_appointment_time(time=time)
                        await RadistonlineMessages.send_message(chat_id=chat_id, text=first_message)
                        await asyncio.sleep(5)
                        await RadistonlineMessages.send_message(chat_id=chat_id, text=second_message)
                        await LeadFetcher.change_lead_status(
                            lead_id=lead_id,
                            status_name='ВЫБРАЛИ ВРЕМЯ'
                        )
                        break
                    elif "False" in response:
                        # Здесь логика неуспешного выбора времени после большого количества попыток
                        await LeadFetcher.change_lead_status(
                            lead_id=lead_id,
                            status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР'
                        )
                        logger.info(f"Изменили статус задачи с ID {lead_id} на Требуется менеджер, так как не смогли "
                                    f"договориться насчёт времени приема")
                        break
                    else:
                        await RadistonlineMessages.send_message(chat_id=chat_id, text=response)
                        zoom_image = await SendZoomImageChecker.send_zoom_image(response)
                        if zoom_image:
                            await RadistonlineMessages.send_image(chat_id, settings.ZOOM_IMAGE_URL)
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
