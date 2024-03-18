import asyncio
import uuid

from datetime import datetime
from werkzeug.datastructures import ImmutableMultiDict

from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.contacts import ContactFetcher
from src.api.amoCRM.pipelines import PipelineFetcher
from src.api.amoCRM.custom_fields import CustomFieldsFetcher

from src.api.radistonline.messages import RadistonlineMessages
from src.api.radistonline.chats import RadistOnlineChats


from src.core.config import logger
from src.core.texts import FirstStepTexts
from src.dialog.steps.first.llm_instructor import SurveyInitialCheck

from src.orm.crud.amo_leads import AmoLeadsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD
from src.orm.crud.chat_steps import ChatStepsCRUD
from src.orm.crud.amo_contacts import AmoContactsCRUD


async def amo_data_processing(data):
    """
    В этой функции выстраивается вся логика обработки новых сделок и смены статусов сделок в amoCRM

    :param data: Словарь с сырыми данными для обработки
    """
    # Преобразуем полученные данные в человеческий вид
    data = ImmutableMultiDict(data).to_dict()

    # Выявляем тип полученных данных при помощи принципа EAFP
    try:
        # Обработка получения новой задачи
        new_lead_id = data['leads[add][0][id]']
        new_lead_data = await LeadFetcher.get_lead(lead_id=new_lead_id)

        # Берём ID контакта для получения данных
        contact_id = new_lead_data['_embedded']['contacts'][0]['id']
        contact_data = await ContactFetcher.get_contact_by_id(contact_id)
        phone_number = contact_data['custom_fields_values'][0]['values'][0]['value']
        contact_name = contact_data['name']

        # Имя нового контакта в Radist.Online должно быть не меньше 5 знаков, добавляем недостающие по необходимости
        name = contact_name + '_' * (5 - len(contact_name)) if len(contact_name) < 5 else contact_name

        # Проверяем, существует ли уже номер телефона в базе контактов amoCRM
        is_existed = await ContactFetcher.check_contact_already_exist_by_phone(contact_id, phone_number)
        if is_existed:

            # Здесь мы просто меняем статус задачи, больше действий не требуется
            await LeadFetcher.change_lead_status(
                lead_id=new_lead_id,
                status_name='Требуется менеджер'
            )
            logger.info(f"Изменили статус задачи с ID {new_lead_id} на Требуется менеджер")
        else:
            # Меняем статус задачи на "Старт Нейро"
            await LeadFetcher.change_lead_status(
                lead_id=new_lead_id,
                status_name='Старт Нейро'
            )
            logger.info(f"Изменили статус задачи с ID {new_lead_id} на Старт Нейро")

            # Сохраняем данные нового лида
            await AmoLeadsCRUD.save_new_lead(new_lead_data, contact_data)
            logger.info(f"Сохранили данные по новому лиду с ID {new_lead_id}")

            # Засыпаем на 4 минуты, пока amoCRM занимается сборкой данных по клиенту
            await asyncio.sleep(5)

            # Теперь необходимо проверить, есть ли у клиента полностью заполненный опрос
            survey_data = await CustomFieldsFetcher.get_survey_lead_fields(lead_id=new_lead_id)

            if survey_data:

                # Если опрос заполнен, нам необходимо провести первичную проверку данных
                baby_age_month, segment, for_online = await SurveyInitialCheck.get_survey_initial_check(survey_data)

                # Возраст ребёнка мы высчитываем в количестве месяцев для более надёжной проверки.
                if baby_age_month < 42 or segment == "C" or not for_online:

                    # Если сделка не прошла проверку, то просто меняем статус
                    await LeadFetcher.change_lead_status(
                        lead_id=new_lead_id,
                        status_name='Требуется менеджер'
                    )
                    logger.info(f"Изменили статус задачи с ID {new_lead_id} на Требуется менеджер, "
                                f"так как сделка не прошла первичную проверку")
                else:
                    # Сохраняем сегмент в amoCRM
                    await CustomFieldsFetcher.save_survey_lead_fields(new_lead_id, {'segment': segment})

                    # Cоздаём новый чат в Radist.Online и начинаем диалог с сообщения при заполненном опросе
                    _, chat_id = await RadistOnlineChats.create_new_chat(
                        name=name,
                        phone=phone_number
                    )
                    # Сохраняем chat_id в БД
                    await AmoLeadsCRUD.save_new_chat_id(
                        lead_id=int(new_lead_id) if type(new_lead_id) is str else new_lead_id,
                        chat_id=int(chat_id) if type(chat_id) is str else chat_id
                    )
                    # Сбор данных о ребенке для БД
                    child_info = {
                        "city": survey_data["Имя ребёнка"],
                        "child_name": survey_data["Дата рождения"],
                        "child_birth_date": survey_data["Дата рождения"],
                        "doctor_enquiry": survey_data["Подробнее о запросе"],
                        "diagnosis": survey_data['Диагноз (если есть)'],
                        "segment": segment,
                    }
                    # Сохраняем данные о ребенке в БД
                    await AmoContactsCRUD.update_contact_values(contact_id=contact_id,
                                                                update_columns=child_info)

                    # Получаем текст первого сообщения и отправляем его в указанный chat_id
                    first_message_text = FirstStepTexts.return_first_message_text(
                        is_survey=True,
                        diagnosis=survey_data['Подробнее о запросе']
                    )
                    await RadistonlineMessages.send_message(
                        chat_id=chat_id,
                        text=first_message_text
                    )
                    # Сохраняем отправленное сообщение в БД
                    data = {
                        "event": {
                            "chat_id": chat_id,
                            "message": {
                                "message_id": str(uuid.uuid4()),
                                "direction": "outbound",
                                "created_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                                "text": {
                                    "text": first_message_text
                                }
                            },
                        }
                    }
                    await RadistMessagesCRUD.save_new_message(data)
                    logger.info(f"Отправили и сохранили первое сообщение в сделке с ID {new_lead_id}")

                    # Переводим пользователя в шаг 1.0, в котором ему нужно просто ответить Да или Нет.
                    await ChatStepsCRUD.create(lead_id=new_lead_id,
                                               step="1.0")

            else:
                # Здесь мы создаём новый чат в Radist.Online и начинаем диалог с сообщения при незаполненном опросе
                _, chat_id = await RadistOnlineChats.create_new_chat(
                    name=name,
                    phone=phone_number
                )

                # Сохраняем chat_id в БД
                await AmoLeadsCRUD.save_new_chat_id(
                    lead_id=int(new_lead_id) if type(new_lead_id) is str else new_lead_id,
                    chat_id=int(chat_id) if type(chat_id) is str else chat_id
                )

                # Получаем текст первого сообщения и отправляем его в указанный chat_id
                first_message_text = FirstStepTexts.return_first_message_text(
                    is_survey=False
                )
                await RadistonlineMessages.send_message(
                    chat_id=chat_id,
                    text=first_message_text
                )
                # Сохраняем отправленное сообщение в БД
                data = {
                    "event": {
                        "chat_id": chat_id,
                        "message": {
                            "message_id": str(uuid.uuid4()),
                            "direction": "outbound",
                            "created_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                            "text": {
                                "text": first_message_text
                            }
                        },
                    }
                }
                await RadistMessagesCRUD.save_new_message(data)
                logger.info(f"Отправили и сохранили первое сообщение в незаполненной сделке с ID {new_lead_id}")

                # Сохраняем шаг в диалоге у конкретной сделки
                await ChatStepsCRUD.create(lead_id=new_lead_id, step="1.1")

    except KeyError:
        # Обработка смены статуса задачи c сохранением нового ID в базу данных
        lead_id = int(data['leads[status][0][id]'])  # noqa
        # Проверяем наличие лида в БД
        lead_exist = await AmoLeadsCRUD.get_lead_by_id(lead_id)
        if lead_exist:
            new_status_id = int(data['leads[status][0][status_id]'])  # noqa
            new_status_name = await PipelineFetcher.get_pipeline_status_name_by_id(new_status_id)

            await AmoLeadsCRUD.change_lead_status(lead_id, new_status_id)
            logger.info(f"У задачи с ID {lead_id} изменился статус. Новый статус: {new_status_name}")
        else:
            logger.info(f"Задача с ID {lead_id} отсутствует в БД, смена статуса невозможна")
