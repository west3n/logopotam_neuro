import asyncio
import pytz

from datetime import datetime
from typing import Union

from openai import AsyncAssistantEventHandler, BadRequestError, APIError
from openai.types.beta.threads import Message

from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.tags import TagsFetcher
from src.api.amoCRM.tasks import TaskFetcher
from src.api.radistonline.messages import RadistonlineMessages
from src.api.bubulearn.slots import BubulearnSlotsFetcher

from src.core.config import settings, openai_clients, logger
from src.core.texts import RegistrationAssistantTexts, TaskTexts

from src.dialog.objections.llm_instructor import JSONChecker, SurveyInitialCheck, GetSlotId, SurveyCollector
from src.orm.crud.amo_leads import AmoLeadsCRUD

from src.orm.crud.radist_chats import RadistChatsCRUD, ChatStepsCRUD
from src.orm.crud.slots import SlotsCRUD

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


def slots_formatting(slots):
    for slot in slots:
        slot['datetime'] = datetime.strptime(slot['start_time'], '%d.%m.%Y %H:%M')
    slots.sort(key=lambda x: x['datetime'])
    result = '\n'.join(f"{slot['weekday']} - {slot['start_time']}" for slot in slots)
    return result


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
    async def create_message(thread_id: str, content: str):
        new_message = await openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role='user',
            content=content
        )
        return new_message.id

    @staticmethod
    async def get_survey_response_stream(
            new_messages: Union[list, str], chat_id: int, lead_id: int, contact_id: int
    ):
        """
        Функция для получения ответа от ассистента при заполнении анкеты
        :param new_messages: Список новых сообщений
        :param chat_id: ID чата
        :param lead_id: ID сделки
        :param contact_id: ID контакта
        """
        thread_id = await RadistChatsCRUD.get_thread_id(chat_id)
        if not thread_id:
            thread_id = await Assistant.create_thread()
            await RadistChatsCRUD.save_new_thread(chat_id, thread_id)
        content = '\n'.join([i[1] for i in new_messages]) if isinstance(new_messages, list) else new_messages
        while True:
            try:
                await Assistant.create_message(thread_id, content)  # noqa
                start_time = datetime.now()
                async with openai_client.beta.threads.runs.stream(
                        thread_id=thread_id,
                        assistant_id=settings.OPENAI_ASSISTANT_ID,
                        event_handler=AssistantStream(lead_id, chat_id, contact_id, new_messages, start_time),
                ) as stream:
                    await stream.until_done()
                break
            except (BadRequestError, APIError):
                await asyncio.sleep(3)
                continue

    @staticmethod
    async def get_first_registration_message(chat_id: int = None):
        slots, _ = await SlotsCRUD.read_slots()
        moscow_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M')
        weekday = current_day_of_week[datetime.now(pytz.timezone('Europe/Moscow')).weekday()]
        content = f"Московское время: {moscow_time}, {weekday.capitalize()}\n\nCлоты:\n{slots_formatting(slots)}"
        thread_id = await Assistant.create_thread()
        await RadistChatsCRUD.save_new_registration_thread_id(chat_id, thread_id)
        await Assistant.create_message(thread_id, content)
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
                    content=content,
                )
                run = await openai_client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=settings.OPENAI_REGISTRATION_ASSISTANT_ID
                )
        messages = await openai_client.beta.threads.messages.list(thread_id=thread_id)
        response = messages.data[0].content[0].text.value
        await RadistonlineMessages.send_message(chat_id=chat_id, text=response)
        logger.info(f"Отправлено первое сообщение о регистрации в чат {chat_id}: {response}")

    @staticmethod
    async def re_offer_slot(chat_id: int):
        slots, _ = await SlotsCRUD.read_slots()
        moscow_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M')
        weekday = current_day_of_week[datetime.now(pytz.timezone('Europe/Moscow')).weekday()]
        content = f"Московское время: {moscow_time}, {weekday.capitalize()}\n\nCлоты:\n{slots_formatting(slots)}"
        content = f"Ответ клиента: Слот занят\n\n{content}"
        thread_id = await RadistChatsCRUD.get_registration_thread_id(chat_id)
        await Assistant.create_message(thread_id, content)
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
                    content=content,
                )
                run = await openai_client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=settings.OPENAI_REGISTRATION_ASSISTANT_ID
                )
        messages = await openai_client.beta.threads.messages.list(thread_id=thread_id)
        response = messages.data[0].content[0].text.value
        await RadistonlineMessages.send_message(chat_id=chat_id, text=response)
        return response

    @staticmethod
    async def get_registration_response_stream(
            chat_id: int, lead_id: int, contact_id: int, new_messages: list = None):
        """
        Функция для получения ответа от ассистента при регистрации на приём
        :param new_messages:
        :param chat_id: ID чата
        :param lead_id: ID сделки
        :param contact_id: ID контакта
        """
        thread_id = await RadistChatsCRUD.get_registration_thread_id(chat_id)
        slots, _ = await SlotsCRUD.read_slots()
        start_time = datetime.now()
        moscow_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M')
        weekday = current_day_of_week[datetime.now(pytz.timezone('Europe/Moscow')).weekday()]
        content = f"Московское время: {moscow_time}, {weekday.capitalize()}\n\nCлоты:\n{slots_formatting(slots)}"
        # Если нет новых сообщений, значит оно первое и должно быть списком с временем свободных слотов
        if not new_messages:
            message_text = content
        else:
            messages_string = '\n'.join([i[1] for i in new_messages])
            message_text = f"Ответ клиента: {messages_string}\n\n{content}"
        if not thread_id:
            thread_id = await Assistant.create_thread()
            await RadistChatsCRUD.save_new_registration_thread_id(chat_id, thread_id)
        logger.info(f'Сгенерировал сообщение в сделке {lead_id}: {message_text}')
        while True:
            try:
                await Assistant.create_message(thread_id, message_text)
                async with openai_client.beta.threads.runs.stream(
                        thread_id=thread_id,
                        assistant_id=settings.OPENAI_REGISTRATION_ASSISTANT_ID,
                        event_handler=RegistrationAssistantStream(start_time, lead_id, chat_id, contact_id,
                                                                  new_messages)
                ) as stream:
                    await stream.until_done()
                break
            except (BadRequestError, APIError):
                await asyncio.sleep(3)
                continue


class AssistantStream(AsyncAssistantEventHandler):
    def __init__(self, lead_id: int, chat_id: int, contact_id: int, new_messages: list, start_time: datetime):
        self.lead_id = lead_id
        self.chat_id = chat_id
        self.contact_id = contact_id
        self.new_messages = new_messages
        self.new_messages_count = len(new_messages)
        self.counter = 0
        self.start_time = start_time
        super().__init__()

    async def on_message_done(self, message: Message) -> None:
        text = message.content[0].text
        timer_seconds = (datetime.now() - self.start_time).total_seconds()
        logger.info(f"Сгенерирован текст для сделки #{self.lead_id}: {text.value}. Время: {timer_seconds}")
        if timer_seconds < 20:
            await asyncio.sleep(20 - timer_seconds)
        if 'json' in text.value or ('{' in text.value and '}' in text.value):
            try:
                json_data = await JSONChecker.inject_json(text.value)
                logger.info(f"Получил JSON в сделке #{self.lead_id}: {str(json_data)}")
            except Exception as e:
                logger.error(f"Ошибка при обработке JSON {e}. Сделка #{self.lead_id}. Пробуем заново.")
                try:
                    json_data = await JSONChecker.inject_json(text.value)
                except Exception as e:
                    logger.error(
                        f"Повторная ошибка при обработке JSON {e}. Сделка #{self.lead_id}. Пробуем другой метод."
                    )
                    try:
                        json_data = await SurveyCollector.get_survey_data(text.value)
                    except Exception as e:
                        json_data = None
                        logger.error(f"Повторная ошибка при обработке JSON {e}. Сделка #{self.lead_id}.")
                    pass
            try:
                if json_data:
                    await CustomFieldsFetcher.save_survey_lead_fields(self.lead_id, json_data)
                    logger.info(f"Сделка #{self.lead_id}: данные по клиенту сохранены в amoCRM")
            except Exception as e:
                logger.error(f"При сохранении данных по клиенту в сделке {self.lead_id} произошла ошибка: {e}")
                pass
            try:
                survey_complete_text = RegistrationAssistantTexts.survey_completed()
                await RadistonlineMessages.send_message(chat_id=self.chat_id, text=survey_complete_text)
                logger.info(f"Сделка #{self.lead_id}: сообщение об окончании опроса отправлено")
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения об окончании опроса в сделке {self.lead_id}: {e}")
                pass
            try:
                if json_data:
                    baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(
                        json_data)
                    logger.info(
                        f"Сделка #{self.lead_id}: Месяцы: {baby_age_month}, "
                        f"Сегмент: {segment}, Онлайн: {for_online}"
                    )
                else:
                    baby_age_month, segment, for_online = 43, 'A', True
                    logger.error(
                        f"Сделка #{self.lead_id}: Месяцы: {baby_age_month},"
                        f" Сегмент: {segment}, Онлайн: {for_online}"
                    )
            except Exception as e:
                baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(
                    json_data)
                logger.error(
                    f"При получении данных для проверки анкеты "
                    f"клиента в сделке {self.lead_id} произошла ошибка: {e}"
                )
                pass
            # Возраст ребёнка мы высчитываем в количестве месяцев для более надёжной проверки.
            if baby_age_month > 42 and segment != "C" and for_online:
                try:
                    await Assistant.get_first_registration_message(chat_id=self.chat_id)
                    logger.info(f"Сделка #{self.lead_id}: Сообщение о регистрации отправлено")
                except Exception as e:
                    logger.error(
                        f"При отправке сообщения о регистрации в сделке {self.lead_id} произошла ошибка: {e}")
                    pass
                try:
                    await ChatStepsCRUD.update(chat_id=self.chat_id, step="registration")
                    logger.info(f"Сделка #{self.lead_id}: Статус чата обновлен")
                except Exception as e:
                    logger.error(f"При обновлении статуса чата в сделке {self.lead_id} произошла ошибка: {e}")
                    pass
            else:
                if baby_age_month < 42:
                    tag_name = 'младше 3,6'
                elif segment == "C":
                    tag_name = 'сегмент С'
                else:
                    tag_name = 'диагноз'
                # Если сделка не прошла проверку, то просто меняем статус и ставим задачу
                await LeadFetcher.change_lead_status(lead_id=self.lead_id, status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР')
                await TaskFetcher.set_task(lead_id=str(self.lead_id), task_text=TaskTexts.NEED_MANAGER_TEXT)
                await TagsFetcher.add_new_tag(lead_id=str(self.lead_id), tag_name=tag_name)
                logger.info(f"Сделка #{self.lead_id} не прошла первичную проверку. Тег: {tag_name}")
                await AmoLeadsCRUD.delete_lead_and_related_data(self.lead_id)
        else:
            if "False" in text.value or "Otkaz" in text.value:
                tag_name = "вопрос не для нейро"
                if "Otkaz" in text.value:
                    tag_name = "отказ"
                await LeadFetcher.change_lead_status(lead_id=self.lead_id, status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР')
                await TagsFetcher.add_new_tag(lead_id=str(self.lead_id), tag_name=tag_name)
                await TaskFetcher.set_task(lead_id=str(self.lead_id), task_text=TaskTexts.NEED_MANAGER_TEXT)
                logger.info(f"В сделке {self.lead_id} не удалось ответить на вопрос")
                await AmoLeadsCRUD.delete_lead_and_related_data(self.lead_id)
            else:
                await RadistonlineMessages.send_message(
                    chat_id=self.chat_id, text=text.value, new_messages_count=self.new_messages_count
                )
                logger.info(f"Отправили сообщение! Сделка #{self.lead_id}: {text.value}")


class RegistrationAssistantStream(AsyncAssistantEventHandler):
    def __init__(self, start_time: datetime, lead_id: int = None, chat_id: int = None, contact_id: int = None,
                 new_messages: list = None):
        self.lead_id = lead_id
        self.chat_id = chat_id
        self.contact_id = contact_id
        self.new_messages = new_messages
        self.new_messages_count = len(new_messages)
        self.counter = 0
        self.start_time = start_time
        super().__init__()

    async def on_message_done(self, message: Message) -> None:
        text = message.content[0].text
        timer_seconds = (datetime.now() - self.start_time).total_seconds()
        if timer_seconds < 20:
            await asyncio.sleep(20 - timer_seconds)
        if "True" in text.value:
            # Здесь логика после успешного выбора времени
            logger.info(f"В сделке с ID {self.lead_id} клиент выбрал время: {text.value}")
            slot_id = await GetSlotId.get_slot_id(text.value)
            logger.info(f"В сделке с ID {self.lead_id} получен ID слота: {slot_id}")
            time = await BubulearnSlotsFetcher.get_slots(slot_id=slot_id)
            logger.info(f"В сделке с ID {self.lead_id} получен слот: {time}")
            # Проверяем, свободен ли слот
            is_slot_valid = await BubulearnSlotsFetcher.is_slot_free(slot_id=slot_id)
            if not is_slot_valid:
                logger.info(f"В сделке с ID #{self.lead_id} слот уже занят: {slot_id}")
                status_value = await CustomFieldsFetcher.get_neuromanager_status_value(lead_id=self.lead_id)
                if status_value and status_value == "Повторное предложение слота":

                    # В этом случае повторное предложение уже было сделано, поэтому просто меняем статус
                    await LeadFetcher.change_lead_status(lead_id=self.lead_id, status_name='В работе ( не было звонка)')
                    await TagsFetcher.add_new_tag(lead_id=str(self.lead_id), tag_name='не было нужного слота')
                    logger.info(f"В сделке с ID #{self.lead_id} повторное предложение уже было сделано")
                    await AmoLeadsCRUD.delete_lead_and_related_data(self.lead_id)
                else:

                    # В этом случае повторное предложение еще не сделано, поэтому отправляем повторное предложение
                    re_offer = await Assistant.re_offer_slot(chat_id=self.chat_id)
                    logger.info(f"Отправлено повторное предложение слота в чат {self.chat_id}: {re_offer}")
                    # Добавляем пометку о том, что повторное предложение уже было сделано
                    await CustomFieldsFetcher.change_status(lead_id=self.lead_id, text="Повторное предложение слота")
            else:
                if time and slot_id and slot_id != "None":
                    logger.info(f"В сделке с ID #{self.lead_id} выбрал время: {time}")
                    first_message = RegistrationAssistantTexts.approve_appointment_time(
                        time=time
                    )
                    await RadistonlineMessages.send_message(chat_id=self.chat_id, text=first_message)
                    logger.info(f"Отправили сообщение! Сделка #{self.lead_id}: {first_message}")
                    await SlotsCRUD.take_slot(slot_id=slot_id)
                    await LeadFetcher.change_lead_status(lead_id=self.lead_id, status_name='ВЫБРАЛИ ВРЕМЯ')
                    await TagsFetcher.add_new_tag(lead_id=str(self.lead_id), tag_name='Записал_НМ')
                    await TaskFetcher.set_task(lead_id=str(self.lead_id), task_text=TaskTexts.TIME_SELECTED_TEXT)
                    await AmoLeadsCRUD.delete_lead_and_related_data(self.lead_id)
                else:
                    logger.info(f"В сделке с ID #{self.lead_id} слот уже занят: {slot_id}")
                    status_value = await CustomFieldsFetcher.get_neuromanager_status_value(lead_id=self.lead_id)
                    if status_value and status_value == "Повторное предложение слота":

                        # В этом случае повторное предложение уже было сделано, поэтому просто меняем статус
                        await LeadFetcher.change_lead_status(lead_id=self.lead_id,
                                                             status_name='В работе ( не было звонка)')
                        await TagsFetcher.add_new_tag(lead_id=str(self.lead_id), tag_name='не было нужного слота')
                        logger.info(f"В сделке с ID #{self.lead_id} повторное предложение уже было сделано")
                        await AmoLeadsCRUD.delete_lead_and_related_data(self.lead_id)
                    else:
                        # В этом случае повторное предложение еще не сделано, поэтому отправляем повторное предложение
                        re_offer = await Assistant.re_offer_slot(chat_id=self.chat_id)
                        logger.info(f"Отправлено повторное предложение слота в чат {self.chat_id}: {re_offer}")
                        # Добавляем пометку о том, что повторное предложение уже было сделано
                        await CustomFieldsFetcher.change_status(
                            lead_id=self.lead_id, text="Повторное предложение слота"
                        )
        elif "False" in text.value or "Otkaz" in text.value:
            tag_name = "вопрос не для нейро"
            if "Otkaz" in text.value:
                tag_name = "отказ"
            # Здесь логика неуспешного выбора времени после большого количества попыток
            await LeadFetcher.change_lead_status(lead_id=self.lead_id, status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР')
            await TagsFetcher.add_new_tag(lead_id=str(self.lead_id), tag_name=tag_name)
            await TaskFetcher.set_task(lead_id=str(self.lead_id), task_text=TaskTexts.NEED_MANAGER_TEXT)
            logger.info(f"В сделке с ID {self.lead_id} не смогли договориться насчёт времени приема")
            await AmoLeadsCRUD.delete_lead_and_related_data(self.lead_id)
        else:
            await RadistonlineMessages.send_message(
                chat_id=self.chat_id, text=text.value, new_messages_count=self.new_messages_count
            )
            # Здесь проверяем, является ли сообщение ассистента помощью с ZOOM
            if "ноутбука/компьютера" in text.value:
                await RadistonlineMessages.send_image(self.chat_id, settings.ZOOM_IMAGE_URL)
