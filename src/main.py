"""
Для реализации обработки вебхуков мы используем Quart, так как Radist.Online и amoCRM требует делать это асинхронным
методом, в котором необходимо в течение 2-3 секунд отвечать о принятии.
"""
import asyncio

from quart import Quart, request, jsonify
from werkzeug.datastructures import ImmutableMultiDict

from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.contacts import ContactFetcher
from src.core.config import logger

# from src.api.assistant.response import AssistantResponse
# from src.api.radistonline.connect import RadistOnlineConnect


app = Quart(__name__)


# # Здесь отлавливаются события из Radist.Online
# @app.route('/event', methods=['POST'])
# async def event():
#     """
#     Так как обработка данных входящих сообщений от пользователей может происходить гораздо дольше 2-3 секунд,
#     то мы каждую задачу добавляем в очередь и моментально отправляем ответ об успешном приёме данных.
#     :return: 200
#     """
#     data = await request.get_json()
#     app.add_background_task(data_processing, data)
#     logger.info(f"Получили новое событие из Radist.Online с данными: {str(data)}")
#     return jsonify(''), 200


# Здесь отлавливаются события из amoCRM
@app.route('/amocrm', methods=["GET", "POST"])
async def amocrm():
    """
    Так как обработка данных входящих сообщений от пользователей может происходить гораздо дольше 2-3 секунд,
    то мы каждую задачу добавляем в очередь и моментально отправляем ответ об успешном приёме данных.
    :return: 200
    """
    data = await request.form
    logger.webhook(f"Получили новое событие из amoCRM с данными: {str(data)}")
    app.add_background_task(data_processing_amo, data)
    return jsonify(''), 200


# async def data_processing(data):
    # """
    # В этой функции выстраивается вся логика обработки входящего сообщения WhatsApp и отправка ответа пользователю
    #
    # :param data: JSON с данными о входящем сообщении
    # """
    # try:
    #     direction = data['event']['message']['direction']
    #     # Здесь мы устанавливаем триггер только на входящие сообщения
    #     if direction == 'inbound':
    #         chat_id = data['event']['chat_id']
    #         user_prompt = data['event']['message']['text']['text']
    #         print("Получили сообщение от пользователя: ", user_prompt)
    #
    #         # Здесь мы отправляем сообщение Ассистенту
    #         response_text, thread_id = await AssistantResponse.get_response(user_prompt=user_prompt)
    #         print(f"Получил сообщение от ассистента: ", response_text)
    #
    #         # Здесь мы отправляем ответ пользователю
    #         await RadistOnlineConnect.send_message(chat_id, response_text)
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
        new_lead_contact_id = new_lead_data['_embedded']['contacts'][0]['id']
        new_lead_contact_data = await ContactFetcher.get_contact_by_id(new_lead_contact_id)
        phone_number = new_lead_contact_data['custom_fields_values'][0]['values'][0]['value']

        # Проверяем, существует ли указанный номер телефона в базе данных
        # TODO: написать логику проверки номера телефона в базе данных (return: is_existed(True/False))
        is_existed = True
        if is_existed:
            # Здесь мы просто меняем статус задачи, больше действий не требуется
            await LeadFetcher.change_lead_status(
                lead_id=new_lead_id,
                status_name='Требуется менеджер'
            )
            logger.info(f"Изменили статус задачи с ID {new_lead_id} на Требуется менеджер")
        else:
            # TODO: написать логику сохранения данных в БД
            # Засыпаем на 4 минуты, пока amoCRM занимается сборкой данных по клиенту
            await asyncio.sleep(240)

            # Теперь необходимо проверить, есть ли у клиента заполненный опрос
            has_survey = True
            # TODO: написать логику проверки наличия данных по опросу (return: True/False)
            if has_survey:
                # TODO: написать логику проверки возраста ребёнка, определения сегмента клиента и
                #   определения заявок, не предназначенных для онлайн
                #   (return: baby_age (int), segment (A,B,C), for_online(True/False))
                baby_age = 12
                segment = "B"
                for_online = True
                if baby_age < 3.6 or segment == "C" or not for_online:
                    # Здесь мы просто меняем статус задачи, больше действий не требуется
                    # TODO: написать логику смены статуса задачи на "Требуется менеджер"
                    pass
                else:
                    # Здесь мы начинаем диалог с сообщения при заполненном опросе
                    # TODO: написать логику отправки первого сообщения при заполненном опросе клиенту в WhatsApp
                    pass
            else:
                # Здесь мы начинаем диалог с сообщения при незаполненном опросе
                # TODO: написать логику отправки первого сообщения без заполненного опроса клиенту в WhatsApp
                pass

    except KeyError:
        # Обработка смены статуса задачи
        new_status_id = data['leads[status][0][status_id]']
        # TODO: написать логику изменения статуса задачи в базе данных


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000)
