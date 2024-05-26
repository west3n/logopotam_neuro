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

from src.core.config import logger, settings
from src.core.texts import TaskTexts

from src.dialog.objections.assistant import Assistant
from src.dialog.objections.llm_instructor import SurveyInitialCheck

from src.orm.crud.amo_leads import AmoLeadsCRUD
from src.orm.crud.radist_chats import ChatStepsCRUD
from src.orm.crud.amo_contacts import AmoContactsCRUD


async def proceed_new_lead(lead_id, new_status_id=None):
    # Здесь находится логика обработки новых сделок
    new_lead_data = await LeadFetcher.get_lead(lead_id=lead_id)
    try:
        contact_id = new_lead_data['_embedded']['contacts'][0]['id']
    except IndexError:
        await asyncio.sleep(30)
        new_lead_data = await LeadFetcher.get_lead(lead_id=lead_id)
        contact_id = new_lead_data['_embedded']['contacts'][0]['id']
    logger.info(f"ID контакта: {contact_id}")

    contact_data = await ContactFetcher.get_contact_by_id(contact_id)
    contact_name = contact_data['name']
    name = contact_name + '_' * (5 - len(contact_name)) if len(contact_name) < 5 else contact_name
    try:
        phone_number = next(
            (cfv['values'][0]['value'] for cfv in contact_data['custom_fields_values'] if
             cfv['field_name'] == 'Телефон'), None)
    except TypeError:
        phone_number = await ContactFetcher.get_contact_number_by_company(contact_id)

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
    print("utm_source: ", utm_source)
    if utm_source == 'Flocktory' or utm_source is None:
        print("Пропускаем ожидание сборки данных по анкете")
        logger.info(f"Пропускаем ожидание сборки данных по анкете")
        survey_data = None
    else:
        print("Начинаем ожидание сборки данных по анкете")
        logger.info(f"Начинаем ожидание сборки данных по анкете")

        # Теперь необходимо проверить, есть ли у клиента полностью заполненный опрос, проверяя каждые 30
        # секунд пока он не заполнится или не пройдет 5 минут
        survey_data = await CustomFieldsFetcher.get_child_data(lead_id=lead_id)
        print("Данные из анкеты: ", survey_data)
        logger.info(f"Данные из анкеты: {survey_data}")
        timeout = 0
        while survey_data in [{}, None] and timeout < 300:
            await asyncio.sleep(30)
            timeout += 30
            print(f"Ожидаем заполнения анкеты в сделке #{lead_id}. Прошло {timeout} секунд.")
            logger.info(f"Ожидаем заполнения анкеты в сделке #{lead_id}. Прошло {timeout} секунд.")
            survey_data = await CustomFieldsFetcher.get_child_data(lead_id=lead_id)
            print("Данные из анкеты после таймаута: ", survey_data)
            logger.info(f"Данные из анкеты после таймаута: {survey_data}")
            continue
    if survey_data and survey_data != {}:
        # Если опрос заполнен, нам необходимо провести первичную проверку данных
        baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(
            survey_data)
        print(f"Сделка #{lead_id}: Месяцы: {baby_age_month}, Сегмент: {segment}, Онлайн: {for_online}")
        logger.info(f"Сделка #{lead_id}: Месяцы: {baby_age_month}, Сегмент: {segment}, Онлайн: {for_online}")

        # Возраст ребёнка мы высчитываем в количестве месяцев для более надёжной проверки.
        if baby_age_month > 42 and segment != "C" and for_online:

            # Проверка пройдена, создаём новый чат в Radist.Online и сохраняем chat_id в БД
            _, chat_id = await RadistOnlineChats.create_new_chat(
                name=name,
                phone=phone_number
            )
            if chat_id:
                await AmoLeadsCRUD.save_new_chat_id(lead_id=int(lead_id), chat_id=int(chat_id))

                # Начинаем диалог разу с шага выбора слотов
                await ChatStepsCRUD.update(chat_id=chat_id, step="registration")
                await Assistant.get_first_registration_message(chat_id=chat_id)
                print(f"Отправили и сохранили первое сообщение в сделке с ID {lead_id}")
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
                except DBAPIError:
                    child_info['child_birth_date'] = datetime.fromtimestamp(
                        survey_data["Дата рождения"])
                    await AmoContactsCRUD.update_contact_values(
                        contact_id=contact_id,
                        update_columns=child_info
                    )
            else:
                print(f"Не удалось создать чат для сделки #{lead_id} из-за проблем с Radist.Online")
                logger.info(f"Не удалось создать чат для сделки #{lead_id} из-за проблем с Radist.Online")
                return
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
            print(f"Изменили статус задачи с ID {lead_id} на Требуется менеджер, так как сделка не "
                  "прошла первичную проверку")
            logger.info(f"Изменили статус задачи с ID {lead_id} на Требуется менеджер, "
                        f"так как сделка не прошла первичную проверку")
    else:
        print("НЕТ ДАННЫХ О РЕБЕНКЕ")
        # Создаём новый чат в Radist.Online и сохраняем chat_id в БД
        chat_id = await RadistOnlineChats.create_new_chat(
            name=name,
            phone=phone_number
        )
        if chat_id:
            await AmoLeadsCRUD.save_new_chat_id(lead_id=int(lead_id), chat_id=int(chat_id))

            # Здесь первый ассистент начинает работу с незаполненного опроса
            await Assistant.get_survey_response_stream(
                chat_id=chat_id,
                lead_id=lead_id,
                contact_id=contact_id,
                new_messages="Нет данных"
            )
            print(f"Отправили и сохранили первое сообщение в незаполненной сделке с ID {lead_id}")
            logger.info(f"Отправили и сохранили первое сообщение в незаполненной сделке с ID {lead_id}")
            # Переводим пользователя в шаг survey, в котором ассистент отвечает за заполнение опроса.
            await ChatStepsCRUD.update(chat_id=chat_id, step="survey")
        else:
            print(f"Не удалось создать чат для сделки #{lead_id} из-за проблем с Radist.Online")
            logger.info(f"Не удалось создать чат для сделки #{lead_id} из-за проблем с Radist.Online")
            return


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
        print("CHANGE CONTACT: ", data)
        logger.info(f"CHANGE CONTACT: {data}")
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
            print(f"Контакт и сделка {lead_id} переименованы")
            logger.info(f"Контакт и сделка {lead_id} переименованы")
        else:
            pass
    except KeyError:
        # Здесь обрабатываем новую задачу в зависимости от выбранного вебхука и воронки
        try:
            lead_id = data['leads[add][0][id]']
            pipeline_id = int(data['leads[add][0][pipeline_id]'])
            if pipeline_id == settings.LOGOPOTAM_PIPELINE_ID:
                await proceed_new_lead(lead_id)
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
                        await proceed_new_lead(lead_id, new_status_id)
