import asyncio
import pytz

from datetime import datetime
from typing import Union

from openai import AsyncAssistantEventHandler, BadRequestError, APIError
from openai.types.beta.threads import Text

from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.tags import TagsFetcher
from src.api.amoCRM.tasks import TaskFetcher
from src.api.radistonline.messages import RadistonlineMessages
from src.api.bubulearn.slots import BubulearnSlotsFetcher

from src.core.config import settings, openai_clients, logger
from src.core.texts import RegistrationAssistantTexts, TaskTexts

from src.dialog.objections.llm_instructor import JSONChecker, SurveyInitialCheck, GetSlotId

from src.orm.crud.amo_contacts import AmoContactsCRUD
from src.orm.crud.radist_chats import RadistChatsCRUD, ChatStepsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD
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


async def get_child_info(json_data: dict, segment: str):
    try:
        child_info = {
            "city": json_data["Страна/город"],
            "child_name": json_data["Имя ребёнка"],
            "child_birth_date": datetime.strptime(json_data["Дата рождения"], "%Y-%m-%d"),
            "doctor_enquiry": json_data["Подробнее о запросе"],
            "diagnosis": json_data['Диагноз (если есть)'],
            "segment": segment,
        }
    except KeyError:
        child_info = {
            "city": json_data["Страна/город"],
            "child_name": json_data["Имя ребенка"],
            "child_birth_date": datetime.strptime(json_data["Дата рождения"], "%Y-%m-%d"),
            "doctor_enquiry": json_data["Подробнее о запросе"],
            "diagnosis": json_data['Диагноз (если есть)'],
            "segment": segment,
        }
    except ValueError:
        child_info = {
            "city": json_data["Страна/город"],
            "child_name": json_data["Имя ребенка"],
            "child_birth_date": datetime.strptime(json_data["Дата рождения"], "%d.%m.%Y"),
            "doctor_enquiry": json_data["Подробнее о запросе"],
            "diagnosis": json_data['Диагноз (если есть)'],
            "segment": segment,
        }
    return child_info


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
                async with openai_client.beta.threads.runs.stream(
                        thread_id=thread_id,
                        assistant_id=settings.OPENAI_ASSISTANT_ID,
                        event_handler=AssistantStream(lead_id, chat_id, contact_id, new_messages),
                ) as stream:
                    await stream.until_done()
                break
            except (BadRequestError, APIError) as e:
                print(e)
                await asyncio.sleep(3)
                continue

    @staticmethod
    async def get_first_registration_message(chat_id: int):
        slots, _ = await SlotsCRUD.read_slots()
        moscow_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M')
        weekday = current_day_of_week[datetime.now(pytz.timezone('Europe/Moscow')).weekday()]
        content = "Cлоты на неделю: " + slots + f"\n\nСейчас в Москве {moscow_time}, {weekday}"
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
        moscow_time = datetime.now(pytz.timezone('Europe/Moscow')).strftime('%H:%M')
        weekday = current_day_of_week[datetime.now(pytz.timezone('Europe/Moscow')).weekday()]
        content = f"Cлоты: {slots}\n\nМосковское время: {moscow_time}, {weekday}"
        # Если нет новых сообщений, значит оно первое и должно быть списком с временем свободных слотов
        if not new_messages:
            message_text = content
        else:
            messages_string = '\n'.join([i[1] for i in new_messages])
            message_text = f"Ответ клиента: {messages_string}\n\n{content}"
        if not thread_id:
            thread_id = await Assistant.create_thread()
            await RadistChatsCRUD.save_new_registration_thread_id(chat_id, thread_id)
        while True:
            try:
                await Assistant.create_message(thread_id, message_text)
                async with openai_client.beta.threads.runs.stream(
                        thread_id=thread_id,
                        assistant_id=settings.OPENAI_REGISTRATION_ASSISTANT_ID,
                        event_handler=RegistrationAssistantStream(lead_id, chat_id, contact_id, new_messages),
                ) as stream:
                    await stream.until_done()
                break
            except (BadRequestError, APIError):
                await asyncio.sleep(3)
                continue


class AssistantStream(AsyncAssistantEventHandler):
    def __init__(self, lead_id: int, chat_id: int, contact_id: int, new_messages: list):
        self.lead_id = lead_id
        self.chat_id = chat_id
        self.contact_id = contact_id
        self.new_messages = new_messages
        self.new_messages_count = len(new_messages)
        super().__init__()

    async def on_text_done(self, text: Text) -> None:
        # Если за время генерации текста появилось новое сообщение, то с текстом дальше не работаем
        print(f"Сгенерирован текст для сделки #{self.lead_id}: {text.value}")
        logger.info(f"Сгенерирован текст для сделки #{self.lead_id}: {text.value}")
        unanswered_messages = await RadistMessagesCRUD.get_all_unanswered_messages(chat_id=self.chat_id)
        if len(unanswered_messages) > self.new_messages_count:
            pass
        else:
            new_messages_ids = [i[0] for i in unanswered_messages]
            await RadistMessagesCRUD.change_status(new_messages_ids, 'answered')
            is_json = await JSONChecker.check_json(text.value)
            if is_json:
                survey_complete_text = RegistrationAssistantTexts.survey_completed()
                await RadistonlineMessages.send_message(chat_id=self.chat_id, text=survey_complete_text)
                baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(
                    is_json)
                print(baby_age_month, segment, for_online)
                logger.info(
                    f"Сделка #{self.lead_id}: Месяцы: {baby_age_month}, Сегмент: {segment}, Онлайн: {for_online}")
                # Возраст ребёнка мы высчитываем в количестве месяцев для более надёжной проверки.
                if baby_age_month < 42 or segment == "C" or not for_online:

                    # Если сделка не прошла проверку, то просто меняем статус и ставим задачу
                    await LeadFetcher.change_lead_status(lead_id=self.lead_id, status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР')
                    await TaskFetcher.set_task(lead_id=str(self.lead_id), task_text=TaskTexts.NEED_MANAGER_TEXT)
                    print(f"Изменили статус задачи с ID {self.lead_id} на Требуется менеджер, "
                          f"так как сделка не прошла первичную проверку")
                    logger.info(f"Изменили статус задачи с ID {self.lead_id} на Требуется менеджер, "
                                f"так как сделка не прошла первичную проверку")
                else:
                    await Assistant.get_first_registration_message(chat_id=self.chat_id)
                    await ChatStepsCRUD.update(chat_id=self.chat_id, step="registration")
                    child_info = await get_child_info(is_json, segment)
                    await AmoContactsCRUD.update_contact_values(contact_id=self.contact_id,
                                                                update_columns=child_info)
                    _, child_data = await AmoContactsCRUD.get_contact_values(self.contact_id)
                    await CustomFieldsFetcher.save_survey_lead_fields(self.lead_id, child_data)
            else:
                if "False" in text.value or "Otkaz" in text.value:
                    tag_name = "вопрос не для нейро"
                    if "Otkaz" in text.value:
                        tag_name = "отказ"
                    await LeadFetcher.change_lead_status(lead_id=self.lead_id, status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР')
                    await TagsFetcher.add_new_tag(lead_id=str(self.lead_id), tag_name=tag_name)
                    await TaskFetcher.set_task(lead_id=str(self.lead_id), task_text=TaskTexts.NEED_MANAGER_TEXT)
                    logger.info(f"Изменили статус задачи с ID {self.lead_id} на Требуется менеджер, "
                                f"так как не удалось ответить на вопрос")
                else:
                    await RadistonlineMessages.send_message(chat_id=self.chat_id, text=text.value)
                    print(f"Отправили сообщение! Сделка #{self.lead_id}: {text.value}")
                    logger.info(f"Отправили сообщение! Сделка #{self.lead_id}: {text.value}")


class RegistrationAssistantStream(AsyncAssistantEventHandler):
    def __init__(self, lead_id: int, chat_id: int, contact_id: int, new_messages: list):
        self.lead_id = lead_id
        self.chat_id = chat_id
        self.contact_id = contact_id
        self.new_messages = new_messages
        self.new_messages_count = len(new_messages)
        super().__init__()

    async def on_text_done(self, text: Text) -> None:
        # Если за время генерации текста появилось новое сообщение, то с текстом дальше не работаем
        unanswered_messages = await RadistMessagesCRUD.get_all_unanswered_messages(chat_id=self.chat_id)
        if len(unanswered_messages) > self.new_messages_count:
            pass
        else:
            new_messages_ids = [i[0] for i in unanswered_messages]
            await RadistMessagesCRUD.change_status(new_messages_ids, 'answered')
            if "True" in text.value:
                # Здесь логика после успешного выбора времени
                slot_id = await GetSlotId.get_slot_id(text.value)
                time = await BubulearnSlotsFetcher.get_slots(slot_id=slot_id)
                first_message = RegistrationAssistantTexts.approve_appointment_time(
                    time=time
                )
                await RadistonlineMessages.send_message(chat_id=self.chat_id, text=first_message)
                await SlotsCRUD.take_slot(slot_id=slot_id)
                await LeadFetcher.change_lead_status(lead_id=self.lead_id, status_name='ВЫБРАЛИ ВРЕМЯ')
                await TaskFetcher.set_task(lead_id=str(self.lead_id), task_text=TaskTexts.TIME_SELECTED_TEXT)
            elif "False" in text.value or "Otkaz" in text.value:
                tag_name = "вопрос не для нейро"
                if "Otkaz" in text.value:
                    tag_name = "отказ"
                # Здесь логика неуспешного выбора времени после большого количества попыток
                await LeadFetcher.change_lead_status(lead_id=self.lead_id, status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР')
                await TagsFetcher.add_new_tag(lead_id=str(self.lead_id), tag_name=tag_name)
                await TaskFetcher.set_task(lead_id=str(self.lead_id), task_text=TaskTexts.NEED_MANAGER_TEXT)
                logger.info(f"Изменили статус задачи с ID {self.lead_id} на Требуется менеджер, так как не смогли "
                            f"договориться насчёт времени приема")
            else:
                await RadistonlineMessages.send_message(chat_id=self.chat_id, text=text.value)
                # Здесь проверяем, является ли сообщение ассистента помощью с ZOOM
                if "ноутбука/компьютера" in text.value:
                    await RadistonlineMessages.send_image(self.chat_id, settings.ZOOM_IMAGE_URL)
