"""
Для реализации обработки вебхуков мы используем Quart, так как Radist.Online и amoCRM требует делать это асинхронным
методом, в котором необходимо в течение 2-3 секунд отвечать о принятии.
"""
import asyncio

from quart import Quart, request, jsonify
from werkzeug.datastructures import ImmutableMultiDict

from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.contacts import ContactFetcher
from src.api.amoCRM.pipelines import PipelineFetcher
from src.api.amoCRM.custom_fields import CustomFieldsFetcher

from src.api.radistonline.messages import RadistonlineMessages
from src.api.radistonline.chats import RadistOnlineChats

# from src.neuroclasses.neuro_assistant import Assistant
from src.neuroclasses.neuro_instructor import SurveyInitialCheck

from src.core.config import logger
from src.core.texts import FirstMessageTexts

from src.orm.crud.amo_leads import AmoLeadsCRUD

app = Quart(__name__)


# Здесь отлавливаются события из Radist.Online
@app.route('/radist', methods=['POST'])
async def event():
    """
    Так как обработка данных входящих сообщений от пользователей может происходить гораздо дольше 2-3 секунд,
    то мы каждую задачу добавляем в очередь и моментально отправляем ответ об успешном приёме данных.
    :return: 200
    """
    data = await request.get_json()
    app.add_background_task(data_processing, data)
    logger.info(f"Получили новое событие из Radist.Online с данными: {str(data)}")
    return jsonify(''), 200


# Здесь отлавливаются события из amoCRM
@app.route('/amocrm', methods=["POST"])
async def amocrm():
    """
    Так как обработка данных входящих сообщений от пользователей может происходить гораздо дольше 2-3 секунд,
    то мы каждую задачу добавляем в очередь и моментально отправляем ответ об успешном приёме данных.
    :return: 200
    """
    data = await request.form
    logger.info(f"Получили новое событие из amoCRM с данными: {str(data)}")
    app.add_background_task(data_processing_amo, data)
    return jsonify(''), 200


async def data_processing(data):
    """
    В этой функции выстраивается вся логика обработки входящего сообщения WhatsApp и отправка ответа пользователю

    :param data: JSON с данными о входящем сообщении
    """
    print(data)
    # try:
    #     direction = data['event']['message']['direction']
    #     # Здесь мы устанавливаем триггер только на входящие сообщения
    #     if direction == 'inbound':
    #         chat_id = data['event']['chat_id']
    #         user_prompt = data['event']['message']['text']['text']
    #         print("Получили сообщение от пользователя: ", user_prompt)
    #
    #         # Здесь мы отправляем сообщение Ассистенту
    #         response_text, thread_id = await Assistant.get_response(user_prompt=user_prompt)
    #         print(f"Получил сообщение от ассистента: ", response_text)
    #
    #         # Здесь мы отправляем ответ пользователю
    #         await RadistonlineMessages.send_message(chat_id, response_text)
    #         print(f"Ответ пользователю отправлен!")
    # except KeyError:
    #     print(data)


async def data_processing_amo(data):
    """
    В этой функции выстраивается вся логика обработки новых задач и смены статусов задач в amoCRM

    :param data: Словарь с сырыми данными для обработки
    """
    # Преобразуем полученные данные в человеческий вид
    data = ImmutableMultiDict(data).to_dict()

    # Выявляем тип полученных данных при помощи принципа EAFP
    try:
        # Обработка получения новой задачи
        new_lead_id = data['leads[add][0][id]']
        new_lead_data = await LeadFetcher.get_lead(lead_id=new_lead_id)

        # Меняем статус задачи на "Старт Нейро"
        await LeadFetcher.change_lead_status(
            lead_id=new_lead_id,
            status_name='Старт Нейро'
        )
        logger.info(f"Изменили статус задачи с ID {new_lead_id} на Старт Нейро")

        # Берём ID контакта для получения данных
        contact_id = new_lead_data['_embedded']['contacts'][0]['id']
        contact_data = await ContactFetcher.get_contact_by_id(contact_id)
        phone_number = contact_data['custom_fields_values'][0]['values'][0]['value']
        contact_name = contact_data['name']

        # Имя нового контакта в Radist.Online должно быть не меньше 5 знаков, поэтому добавляем до необходимого минимума
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
                    # Здесь мы создаём новый чат в Radist.Online и начинаем диалог с сообщения при заполненном опросе
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
                    first_message_text = FirstMessageTexts.return_first_message_text(
                        is_survey=True,
                        diagnosis=survey_data['Подробнее о запросе']
                    )
                    await RadistonlineMessages.send_message(
                        chat_id=chat_id,
                        text=first_message_text
                    )
                    logger.info(f"Отправили первое сообщение в сделке с ID {new_lead_id}")
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
                first_message_text = FirstMessageTexts.return_first_message_text(
                    is_survey=False
                )
                await RadistonlineMessages.send_message(
                    chat_id=chat_id,
                    text=first_message_text
                )
                logger.info(f"Отправили первое сообщение в сделке с ID {new_lead_id}")

    except KeyError:
        # Обработка смены статуса задачи c сохранением нового ID в базу данных
        lead_id = int(data['leads[status][0][id]'])
        new_status_id = int(data['leads[status][0][status_id]'])
        new_status_name = await PipelineFetcher.get_pipeline_status_name_by_id(new_status_id)

        await AmoLeadsCRUD.change_lead_status(lead_id, new_status_id)
        logger.info(f"У задачи с ID {lead_id} изменился статус. Новый статус: {new_status_name}")


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000)
