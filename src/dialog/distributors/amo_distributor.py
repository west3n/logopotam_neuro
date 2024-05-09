import asyncio

from datetime import datetime

from sqlalchemy.exc import DBAPIError

from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.contacts import ContactFetcher
from src.api.amoCRM.pipelines import PipelineFetcher
from src.api.amoCRM.custom_fields import CustomFieldsFetcher
from src.api.radistonline.chats import RadistOnlineChats

from src.core.config import logger, settings

from src.dialog.objections.assistant import Assistant
from src.dialog.objections.llm_instructor import SurveyInitialCheck

from src.orm.crud.amo_leads import AmoLeadsCRUD
from src.orm.crud.radist_chats import ChatStepsCRUD
from src.orm.crud.amo_contacts import AmoContactsCRUD

from werkzeug.datastructures import ImmutableMultiDict


# async def search_doubles(phone_number):
#     """
#     Приводит любой номер телефона в формат +xxxxxxxxxxxx для поиска дублей.
#     """
#     print("Номер телефона до: ", phone_number)
#     phone_number = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
#     print("Номер телефона после: ", phone_number)
#     result = await DoublesSearchCRUD.search_double(phone_number)
#     if result:
#         return True
#     else:
#         await DoublesSearchCRUD.add_phone(phone_number)
#         return False


async def amo_data_processing(data):
    """
    В этой функции выстраивается вся логика обработки новых сделок и смены статусов сделок в amoCRM

    :param data: Словарь с сырыми данными для обработки
    """
    # Преобразуем полученные данные в человеческий вид и получаем ID новой сделки
    data = ImmutableMultiDict(data).to_dict()

    # Получаем ID новой сделки
    try:
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
                    # Обработка получения новой задачи
                    new_lead_data = await LeadFetcher.get_lead(lead_id=lead_id)
                    # Берём ID контакта для получения данных
                    try:
                        contact_id = new_lead_data['_embedded']['contacts'][0]['id']
                    except IndexError:
                        await asyncio.sleep(60)
                        new_lead_data = await LeadFetcher.get_lead(lead_id=lead_id)
                        contact_id = new_lead_data['_embedded']['contacts'][0]['id']
                    print("ID контакта: ", contact_id)
                    logger.info(f"ID контакта: {contact_id}")
                    contact_data = await ContactFetcher.get_contact_by_id(contact_id)
                    contact_name = contact_data['name']
                    name = contact_name + '_' * (5 - len(contact_name)) if len(contact_name) < 5 else contact_name
                    print("Имя контакта: ", contact_name)
                    logger.info(f"Имя контакта: {contact_name}")
                    try:
                        phone_number = next((cfv['values'][0]['value'] for cfv in contact_data['custom_fields_values'] if
                                             cfv['field_name'] == 'Телефон'), None)
                    except TypeError:
                        phone_number = await ContactFetcher.get_contact_number_by_company(contact_id)
                    # Удаляем лишние знаки из номера телефона
                    if "Доп.информация:," in phone_number:
                        phone_number = phone_number.replace(" Доп.информация:,", "")
                    # Сохраняем данные нового лида и меняем его статус
                    await AmoLeadsCRUD.save_new_lead(new_lead_data, contact_data, phone_number)
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
                        baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(survey_data)
                        print(baby_age_month, segment, for_online)
                        # Возраст ребёнка мы высчитываем в количестве месяцев для более надёжной проверки.
                        if baby_age_month < 42 or segment == "C" or not for_online:
                            # Если сделка не прошла проверку, то просто меняем статус
                            await LeadFetcher.change_lead_status(
                                lead_id=lead_id,
                                status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР'
                            )
                            print("Изменили статус задачи с ID {lead_id} на Требуется менеджер, так как сделка не "
                                  "прошла первичную проверку")
                            logger.info(f"Изменили статус задачи с ID {lead_id} на Требуется менеджер, "
                                        f"так как сделка не прошла первичную проверку")
                        else:
                            # Сохраняем сегмент в amoCRM
                            await CustomFieldsFetcher.save_survey_lead_fields(lead_id, {'segment': segment})

                            # Cоздаём новый чат в Radist.Online и начинаем диалог с сообщения при заполненном опросе
                            _, chat_id = await RadistOnlineChats.create_new_chat(
                                name=name,
                                phone=phone_number
                            )
                            # Сохраняем chat_id в БД
                            await AmoLeadsCRUD.save_new_chat_id(
                                lead_id=int(lead_id) if isinstance(lead_id, str) else lead_id,
                                chat_id=int(chat_id) if isinstance(chat_id, str) else chat_id
                            )
                            # Сбор данных о ребенке для БД
                            child_info = {
                                "city": survey_data["Страна/город"],
                                "child_name": survey_data["Имя ребёнка"],
                                "child_birth_date": survey_data["Дата рождения"],
                                "doctor_enquiry": survey_data["Подробнее о запросе"],
                                "diagnosis": survey_data['Диагноз (если есть)'],
                                "segment": segment,
                            }
                            # Сохраняем данные о ребенке в БД
                            try:
                                await AmoContactsCRUD.update_contact_values(
                                    contact_id=contact_id,
                                    update_columns=child_info
                                )
                            except DBAPIError:
                                child_info['child_birth_date'] = datetime.fromtimestamp(survey_data["Дата рождения"])
                                await AmoContactsCRUD.update_contact_values(
                                    contact_id=contact_id,
                                    update_columns=child_info
                                )
                            # Здесь первый ассистент начинает работу с заполненного опроса
                            await Assistant.get_survey_response_stream(
                                chat_id=chat_id,
                                lead_id=lead_id,
                                contact_id=contact_id,
                                new_messages=str(survey_data)
                            )
                            print(f"Отправили и сохранили первое сообщение в сделке с ID {lead_id}")
                            logger.info(f"Отправили и сохранили первое сообщение в сделке с ID {lead_id}")

                            # Переводим пользователя в шаг survey, в котором ассистент отвечает за заполнение опроса.
                            await ChatStepsCRUD.update(chat_id=chat_id, step="survey")
                    else:
                        print("НЕТ ДАННЫХ О РЕБЕНКЕ")
                        # Здесь мы начинаем диалог с сообщения при незаполненном опросе
                        _, chat_id = await RadistOnlineChats.create_new_chat(
                            name=name,
                            phone=phone_number
                        )

                        # Сохраняем chat_id в БД
                        await AmoLeadsCRUD.save_new_chat_id(
                            lead_id=int(lead_id) if isinstance(lead_id, str) else lead_id,
                            chat_id=int(chat_id) if isinstance(chat_id, str) else chat_id
                        )

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

    # Здесь возвращаем старые имена сделкам и контактам
    except KeyError:
        try:
            lead_id = data['leads[update][0][id]']
            lead_renamed = await AmoLeadsCRUD.get_lead_by_id(int(lead_id), renamed=True)
            if lead_renamed:
                await LeadFetcher.change_lead_name(lead_id=lead_id, new_name=lead_renamed[0])
                await AmoLeadsCRUD.change_renamed_status(int(lead_id))
                print(f"Лид {lead_id} переименован")
                logger.info(f"Лид {lead_id} переименован")
            else:
                pass
        except KeyError:
            contact_id = data['contacts[update][0][id]']
            contact_renamed = await AmoContactsCRUD.get_renamed_contact(int(contact_id))
            if contact_renamed:
                await ContactFetcher.rename_contact(contact_id=contact_id, new_name=contact_renamed[0])
                await AmoContactsCRUD.changed_renamed_status(int(contact_id))
                print(f"Контакт {contact_id} переименован")
                logger.info(f"Контакт {contact_id} переименован")
            else:
                pass
