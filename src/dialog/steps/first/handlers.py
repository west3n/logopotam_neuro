"""
Первым шагом общения с клиентом является выяснение базовых данных для заполнения анкеты в amoCRM. Этот шаг
используется лишь в случае, когда новая сделка в amoCRM приходит с пустой анкетой. В случае, когда анкета уже
была заполнена, первый шаг пропускается.
"""
import asyncio

from src.api.amoCRM.leads import LeadFetcher
from src.dialog.steps.first.llm_instructor import SurveyConfirmation, SurveyFullCheck, SurveyInitialCheck

from src.orm.crud.amo_contacts import AmoContactsCRUD
from src.orm.crud.radist_chats import ChatStepsCRUD

from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.api.radistonline.messages import RadistonlineMessages

from src.core.config import openai_clients, logger
from src.core.texts import FirstStepTexts, SecondStepTexts


async def step_1_0_handler(messages_text: str, chat_id: int, lead_id: int):
    """
    В этой функции мы используем инструктора, который обрабатывает подтверждение правильности анкеты от пользователя
    :param messages_text: Текст сообщения WhatsApp
    :param chat_id: ID чата в Radist.Online
    :param lead_id: ID сделки в amoCRM
    """
    instructor_answer = await SurveyConfirmation.get_survey_confirmation(messages_text)

    if instructor_answer:
        # Если ответ от пользователя положительный, переводим его на шаг 2.0 и отправляем ответное сообщение
        await RadistonlineMessages.send_message(
            chat_id=chat_id,
            text=SecondStepTexts.FIRST_MESSAGE_TEXT
        )
        await ChatStepsCRUD.update(chat_id, "2.0")
        logger.info(f"Перевели пользователя с ID чата {chat_id} на шаг 2.0")
    else:
        # Если ответ от пользователя отрицательный, то отдаём сделку менеджеру
        await LeadFetcher.change_lead_status(
            lead_id=lead_id,
            status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР'
        )
        logger.info(f"Изменили статус задачи с ID {lead_id} на Требуется менеджер, "
                    f"так как пользователь не подтвердил данные по анкете")


async def step_1_1_handler(messages_text: str, contact_id: int, chat_id: int, lead_id: int):
    """
    В этой функции мы используем инструктора для обработки данных для заполнения анкеты, шаг 1.1
    :param messages_text: Текст сообщений, полученный в WhatsApp
    :param contact_id: ID контакта клиента
    :param chat_id: ID чата клиента
    :param lead_id: ID сделки
    """
    client = openai_clients.OPENAI_ASYNC_CLIENT

    # Здесь мы получаем данные от инструктора, передав ему текст сообщения (или сообщений)
    instructor_answer = await SurveyFullCheck.get_survey_full_check(messages_text)
    answers = {
        "child_name": instructor_answer.name,
        "child_birth_date": instructor_answer.age,
        "city": instructor_answer.city,
        "doctor_enquiry": instructor_answer.problem,
        "diagnosis": instructor_answer.neurologist_observation
    }
    print(answers)

    # Создаём 2 словаря для распределения полученных ответов на отвеченные и неотвеченные
    answered_values = {}
    unanswered_values = {}
    for key, value in answers.items():
        if value:
            answered_values[key] = value
        else:
            unanswered_values[key] = value

    # Записываем все отвеченные поля в БД
    if answered_values:
        await AmoContactsCRUD.update_contact_values(contact_id, answered_values)
    print(answered_values)

    # Неотвеченные поля нам необходимо сравнить с данными, которые уже могли быть записаны в БД, найти совпадения
    # и отдать их в обработку в GPT для составления нового вопроса в случае, если клиент предоставил не все нужные
    # данные
    if unanswered_values:
        unanswered_fields_1 = unanswered_values.keys()
        unanswered_fields_2, _ = await AmoContactsCRUD.get_contact_values(contact_id)
        unanswered_fields_complete = list(set(unanswered_fields_1) & set(unanswered_fields_2))

        # Если есть незаполненные поля, то генерируем уточняющий вопрос с учетом незаполненных полей
        if unanswered_fields_complete:
            answers = {
                "child_name": "Имя ребёнка",
                "child_birth_date": "Дата рождения ребёнка",
                "city": "Город",
                "doctor_enquiry": "Какую проблему хотите решить с логопедом",
                "diagnosis": "Наблюдается ли ребенок у невролога"
            }
            gpt_answers = ", ".join(answers[field] for field in list(unanswered_fields_complete))
            completion = await client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": f"{FirstStepTexts.SYSTEM_PROMPT}"},
                    {
                        "role": "assistant",
                        "content": FirstStepTexts.return_first_message_text(is_survey=False)
                    },
                    {
                        "role": "user",
                        "content": f"Данные, которые мы не получили: {gpt_answers}\n"
                    }
                ]
            )

            # Отправляем клиенту полученный от GPT ответ
            await RadistonlineMessages.send_message(
                chat_id=chat_id,
                text=completion.choices[0].message.content
            )

        # Если все поля заполнены, то берём все данные из БД, сохраняем их в amoCRM и валидируем данные анкеты
        else:
            _, child_data = await AmoContactsCRUD.get_contact_values(contact_id)
            survey_data = await CustomFieldsFetcher.save_survey_lead_fields(lead_id, child_data)
            baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(survey_data)

            # Возраст ребёнка мы высчитываем в количестве месяцев для более надёжной проверки.
            if baby_age_month < 42 or segment == "C" or not for_online:

                # Если сделка не прошла проверку, то просто меняем статус и сохраняем сегмент
                await LeadFetcher.change_lead_status(
                    lead_id=lead_id,
                    status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР'
                )
                logger.info(f"Изменили статус задачи с ID {lead_id} на Требуется менеджер, "
                            f"так как сделка не прошла первичную проверку")

            # Если проверка пройдена, то отправляем клиенту второе сообщение
            else:
                await RadistonlineMessages.send_message(
                    chat_id=chat_id,
                    text=SecondStepTexts.FIRST_MESSAGE_TEXT
                )
                await asyncio.sleep(5)
                await RadistonlineMessages.send_message(
                    chat_id=chat_id,
                    text=SecondStepTexts.FIRST_MESSAGE_QUESTION_TEXT
                )
                await ChatStepsCRUD.update(chat_id, "2.0")
            # Сохраняем сегмент в БД и amoCRM
            await AmoContactsCRUD.update_contact_values(contact_id, {'segment': segment})
            await CustomFieldsFetcher.save_survey_lead_fields(lead_id, {'segment': segment})
    # Это исключение отработает только в случае, если клиент с первого раза указал все необходимые поля
    else:
        survey_data = await CustomFieldsFetcher.save_survey_lead_fields(lead_id, answers)
        baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(survey_data)

        # Возраст ребёнка мы высчитываем в количестве месяцев для более надёжной проверки.
        if baby_age_month < 42 or segment == "C" or not for_online:

            # Если сделка не прошла проверку, то просто меняем статус и сохраняем сегмент
            await LeadFetcher.change_lead_status(
                lead_id=lead_id,
                status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР'
            )
            logger.info(f"Изменили статус задачи с ID {lead_id} на Требуется менеджер, "
                        f"так как сделка не прошла первичную проверку")

        # Если проверка пройдена, то отправляем клиенту второе сообщение и сохраняем сегмент в БД
        else:
            await RadistonlineMessages.send_message(
                chat_id=chat_id,
                text=SecondStepTexts.FIRST_MESSAGE_TEXT
            )
            await asyncio.sleep(5)
            await RadistonlineMessages.send_message(
                chat_id=chat_id,
                text=SecondStepTexts.FIRST_MESSAGE_QUESTION_TEXT
            )
            await ChatStepsCRUD.update(chat_id, "2.0")
        # Сохраняем сегмент в БД и amoCRM
        await AmoContactsCRUD.update_contact_values(contact_id, {'segment': segment})
        await CustomFieldsFetcher.save_survey_lead_fields(lead_id, {'segment': segment})