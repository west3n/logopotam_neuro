import asyncio

from datetime import datetime
from sqlalchemy.exc import DBAPIError
from werkzeug.datastructures import ImmutableMultiDict

from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.contacts import ContactFetcher
from src.api.amoCRM.pipelines import PipelineFetcher
from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.api.amoCRM.tags import TagsFetcher
from src.api.amoCRM.tasks import TaskFetcher
from src.api.radistonline.chats import RadistOnlineChats
from src.api.radistonline.messages import RadistonlineMessages

from src.core.config import logger, settings
from src.core.texts import TaskTexts

from src.dialog.objections.assistant import Assistant
from src.dialog.objections.llm_instructor import SurveyInitialCheck

from src.orm.crud.amo_leads import AmoLeadsCRUD
from src.orm.crud.radist_chats import ChatStepsCRUD
from src.orm.crud.amo_contacts import AmoContactsCRUD


async def chat_id_proceed(chat_id: int, lead_id: int, contact_id: int, survey_data: dict, segment: str):
    await AmoLeadsCRUD.save_new_chat_id(lead_id=int(lead_id), chat_id=int(chat_id))

    # Начинаем диалог разу с шага выбора слотов
    await ChatStepsCRUD.update(chat_id=chat_id, step="registration")
    text = (
        'Здравствуйте! 🤗 Вы заинтересовались бесплатной диагностикой. '
        'Это первый шаг к идеальной речи вашего ребенка!'
        '\n\nМеня зовут Алина, я помогу вам записаться.'
    )
    await RadistonlineMessages.send_message(chat_id=int(chat_id), text=text)
    await Assistant.get_first_registration_message(chat_id=chat_id)
    logger.info(f"Отправили и сохранили первое сообщение в сделке с ID {lead_id}")

    # Собираем и сохраняем данные о ребенке для БД
    child_info = {
        "city": survey_data["Страна/город"],
        "child_name": survey_data["Имя ребёнка"],
        "child_birth_date": survey_data["Дата рождения"],
        "doctor_enquiry": survey_data["Подробнее о запросе"],
        "diagnosis": survey_data['Диагноз (если есть)'],
        "segment": segment,
    }
    try:
        await AmoContactsCRUD.update_contact_values(
            contact_id=contact_id,
            update_columns=child_info
        )
    except DBAPIError as e:
        child_info['child_birth_date'] = datetime.fromtimestamp(
            survey_data["Дата рождения"])
        await AmoContactsCRUD.update_contact_values(
            contact_id=contact_id,
            update_columns=child_info
        )
        logger.error(f"DBAPIError, LEAD ID: {lead_id}: " + str(e))


async def proceed_new_lead(lead_id, new_status_id=None):
    # Здесь находится логика обработки новых сделок
    new_lead_data = await LeadFetcher.get_lead(lead_id=lead_id)
    try:
        contact_id = new_lead_data['_embedded']['contacts'][0]['id']
    except IndexError:
        await asyncio.sleep(30)
        new_lead_data = await LeadFetcher.get_lead(lead_id=lead_id)
        contact_id = new_lead_data['_embedded']['contacts'][0]['id']
    logger.info(f"ID контакта в сделке #{lead_id}: {contact_id}")

    contact_data = await ContactFetcher.get_contact_by_id(contact_id)
    contact_name = contact_data['name']
    name = contact_name + '_' * (5 - len(contact_name)) if len(contact_name) < 5 else contact_name
    try:
        phone_number = next(
            (cfv['values'][0]['value'] for cfv in contact_data['custom_fields_values'] if
             cfv['field_name'] == 'Телефон'), None)
    except TypeError as e:
        phone_number = await ContactFetcher.get_contact_number_by_company(contact_id)
        logger.error(f"TypeError: LEAD ID: {lead_id}: " + str(e))

    # Удаляем лишние знаки из номера телефона
    if "Доп.информация:," in phone_number:
        phone_number = phone_number.replace(" Доп.информация:,", "")

    # Сохраняем данные нового лида и меняем его статус
    await AmoLeadsCRUD.save_new_lead(new_lead_data, contact_data, phone_number)
    if new_status_id:
        await AmoLeadsCRUD.change_lead_status(int(lead_id), int(new_status_id))

    # Если источник 'partner' или 'Flocktory' или его нет, то пропускаем ожидание данных по анкете
    custom_fields = await CustomFieldsFetcher.get_survey_lead_fields(lead_id=lead_id)
    try:
        utm_source = custom_fields['utm_source']
    except (TypeError, KeyError):
        utm_source = None
    if utm_source == 'Flocktory' or utm_source is None:
        logger.info(f"Пропускаем ожидание сборки данных по анкете для сделки #{lead_id}")
        survey_data = None
    else:
        logger.info(f"Начинаем ожидание сборки данных по анкете для сделки #{lead_id}")

        # Теперь необходимо проверить, есть ли у клиента полностью заполненный опрос, проверяя каждые 30
        # секунд пока он не заполнится или не пройдет 5 минут
        survey_data = await CustomFieldsFetcher.get_child_data(lead_id=lead_id)
        logger.info(f"Данные из анкеты в сделке #{lead_id}: {survey_data}")
        timeout = 0
        while survey_data in [{}, None] and timeout < 300:
            await asyncio.sleep(30)
            timeout += 30
            logger.info(f"Ожидаем заполнения анкеты в сделке #{lead_id}. Прошло {timeout} секунд.")
            survey_data = await CustomFieldsFetcher.get_child_data(lead_id=lead_id)
            logger.info(f"Данные из анкеты после таймаута: {survey_data}")
            continue
    if survey_data and survey_data != {}:
        # Если опрос заполнен, нам необходимо провести первичную проверку данных
        baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(
            survey_data)
        logger.info(f"Сделка #{lead_id}: Месяцы: {baby_age_month}, Сегмент: {segment}, Онлайн: {for_online}")
        # Возраст ребёнка мы высчитываем в количестве месяцев для более надёжной проверки.
        if baby_age_month > 42 and segment != "C" and for_online:
            try:
                # Проверка пройдена, создаём новый чат в Radist.Online и сохраняем chat_id в БД
                chat_id = await RadistOnlineChats.create_new_chat(
                    name=name,
                    phone=phone_number
                )
                if chat_id:
                    chat_id = int(chat_id)
                    await chat_id_proceed(chat_id, lead_id, contact_id, survey_data, segment)
                else:
                    # После первой неудачной попытки создания чата в Radist.Online добавляем тайм-аут и пытаемся ещё раз
                    logger.info(f"Ошибка создания чата в сделке #{lead_id}, проблема с Radist.Online, тайм-аут: 300")
                    await asyncio.sleep(300)
                    chat_id = await RadistOnlineChats.create_new_chat(
                        name=name,
                        phone=phone_number
                    )
                    if chat_id:
                        chat_id = int(chat_id)
                        await chat_id_proceed(chat_id, lead_id, contact_id, survey_data, segment)
                    else:
                        logger.info(f"Повторная ошибка создания чата в сделке #{lead_id}, проблема с Radist.Online")
                        await CustomFieldsFetcher.change_status(lead_id, phone_number)
                        await LeadFetcher.change_lead_status(lead_id, 'В работе ( не было звонка)')
            except Exception as e:
                logger.error(f"Возникла ошибка при создании чата в Radist.Online: {e}. Сделка #{lead_id}")
        else:
            # Выбираем тег в зависимости от причины неудачного прохождения первичной проверки
            if baby_age_month < 42:
                tag_name = 'младше 3,6'
            elif segment == "C":
                tag_name = 'сегмент С'
            else:
                tag_name = 'диагноз'

            # Меняем статус, ставим задачу и добавляем тег
            await LeadFetcher.change_lead_status(lead_id=lead_id, status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР')
            await TaskFetcher.set_task(lead_id=lead_id, task_text=TaskTexts.NEED_MANAGER_TEXT)
            await TagsFetcher.add_new_tag(lead_id=lead_id, tag_name=tag_name)
            logger.info(f"Сделка #{lead_id} не прошла первичную проверку, тег: {tag_name}")
    else:
        # Создаём новый чат в Radist.Online и сохраняем chat_id в БД
        try:
            chat_id = await RadistOnlineChats.create_new_chat(
                name=name,
                phone=phone_number
            )
            if chat_id:
                chat_id = int(chat_id)

                # Сохраняем chat_id в БД
                await AmoLeadsCRUD.save_new_chat_id(lead_id=int(lead_id), chat_id=int(chat_id))
                await ChatStepsCRUD.update(chat_id=chat_id, step="survey")
                # Здесь первый ассистент начинает работу с незаполненного опроса
                await Assistant.get_survey_response_stream(
                    chat_id=chat_id,
                    lead_id=lead_id,
                    contact_id=contact_id,
                    new_messages="Нет данных"
                )
                logger.info(f"Отправили и сохранили первое сообщение в незаполненной сделке с ID {lead_id}")
                # Переводим пользователя в шаг survey, в котором ассистент отвечает за заполнение опроса.
            else:
                # После первой неудачной попытки создания чата в Radist.Online добавляем тайм-аут и пытаемся ещё раз
                logger.info(f"Ошибка создания чата в сделке #{lead_id}, проблема с Radist.Online, тайм-аут: 300")
                await asyncio.sleep(300)
                chat_id = await RadistOnlineChats.create_new_chat(
                    name=name,
                    phone=phone_number
                )
                if chat_id:
                    chat_id = int(chat_id)

                    # Сохраняем chat_id в БД
                    await AmoLeadsCRUD.save_new_chat_id(lead_id=int(lead_id), chat_id=int(chat_id))
                    await ChatStepsCRUD.update(chat_id=chat_id, step="survey")
                    # Здесь первый ассистент начинает работу с незаполненного опроса
                    await Assistant.get_survey_response_stream(
                        chat_id=chat_id,
                        lead_id=lead_id,
                        contact_id=contact_id,
                        new_messages="Нет данных"
                    )
                    logger.info(f"Отправили и сохранили первое сообщение в незаполненной сделке с ID {lead_id}")
                    # Переводим пользователя в шаг survey, в котором ассистент отвечает за заполнение опроса.
                else:
                    logger.info(f"Повторная ошибка создания чата в сделке #{lead_id}, проблема с Radist.Online")
                    await CustomFieldsFetcher.change_status(lead_id, phone_number)
                    await LeadFetcher.change_lead_status(lead_id, 'В работе ( не было звонка)')
        except Exception as e:
            logger.error(f"Возникла ошибка при создании чата в Radist.Online: {e}. Сделка #{lead_id}")


async def amo_data_processing(data):
    """
    В этой функции выстраивается вся логика обработки новых сделок, смены статусов сделок и изменения контактов в amoCRM

    :param data: Словарь с сырыми данными для обработки
    """
    # Преобразуем полученные данные в человеческий вид и получаем ID новой сделки
    data = ImmutableMultiDict(data).to_dict()
    try:
        # Здесь возвращаем старые имена сделкам и контактам
        contact_id = data['contacts[update][0][id]']
        contact_renamed = await AmoContactsCRUD.get_renamed_contact(int(contact_id))
        if contact_renamed:
            lead_id = await AmoLeadsCRUD.get_lead_id_by_contact_id(contact_id=int(contact_id))
            if lead_id:
                lead_renamed = await AmoLeadsCRUD.get_lead_by_id(int(lead_id))
                if lead_renamed:
                    await LeadFetcher.change_lead_name(lead_id=str(lead_id), new_name=lead_renamed)
                    await AmoLeadsCRUD.change_renamed_status(int(lead_id))
            await ContactFetcher.rename_contact(contact_id=contact_id, new_name=contact_renamed)
            await AmoContactsCRUD.changed_renamed_status(int(contact_id))
            logger.info(f"Контакт {contact_id} и сделка {lead_id} переименованы")
        else:
            pass
    except KeyError:
        # Здесь обрабатываем новую задачу в зависимости от выбранного вебхука и воронки
        await asyncio.sleep(60)
        try:
            lead_id = data['leads[add][0][id]']
            pipeline_id = int(data['leads[add][0][pipeline_id]'])
            if pipeline_id == settings.LOGOPOTAM_PIPELINE_ID:
                new_status_id = int(data['leads[add][0][status_id]'])  # noqa
                new_status_name = await PipelineFetcher.get_pipeline_status_name_by_id(new_status_id)
                if new_status_name != "СТАРТ НЕЙРО":
                    await LeadFetcher.change_lead_status(lead_id=lead_id, status_name='СТАРТ НЕЙРО')
                    logger.info(f"Новая сделка: {lead_id}. Переименовали статус сделки на СТАРТ НЕЙРО")
                    await proceed_new_lead(lead_id)
                else:
                    logger.info(f"Новая сделка #{lead_id} появилась в статусе СТАРТ НЕЙРО, пропускаем ее")
            else:
                logger.info(f"Новая сделка #{lead_id} не относится к воронке Логопотам")

        except KeyError:
            lead_id = data['leads[status][0][id]']
            pipeline_id = int(data['leads[status][0][pipeline_id]'])
            if pipeline_id == settings.LOGOPOTAM_PIPELINE_ID:
                new_status_id = int(data['leads[status][0][status_id]'])  # noqa
                new_status_name = await PipelineFetcher.get_pipeline_status_name_by_id(new_status_id)
                lead_exist = await AmoLeadsCRUD.get_lead_by_id(int(lead_id))
                if lead_exist:
                    await AmoLeadsCRUD.change_lead_status(int(lead_id), new_status_id)
                else:
                    if new_status_name == "СТАРТ НЕЙРО":
                        logger.info(f"NEW LEAD: {lead_id}, {pipeline_id}, {new_status_id}, {new_status_name}")
                        await proceed_new_lead(lead_id, new_status_id)
            else:
                logger.info(f"Новая сделка #{lead_id} не относится к воронке Логопотам")
                pass
