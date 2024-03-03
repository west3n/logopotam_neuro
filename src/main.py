"""
Для реализации обработки вебхуков мы используем Quart, так как Radist.Online требует делать это асинхронным
методом, в котором необходимо в течение 5 секунд отвечать о принятии.
"""
import asyncio

from quart import Quart, request, jsonify

from src.api.assistant.response import AssistantResponse
from src.api.radistonline.connect import RadistOnlineConnect


app = Quart(__name__)


@app.route('/event', methods=['POST'])
async def event():
    """
    Так как обработка данных входящих сообщений от пользователей может происходить гораздо дольше 5 секунд,
    то мы каждую задачу добавляем в очередь и моментально отправляем ответ об успешном приёме данных.
    :return: 200
    """
    data = await request.get_json()
    app.add_background_task(data_processing, data)
    return jsonify(''), 200


async def data_processing(data):
    """
    В этой функции выстраивается вся логика обработки входящего сообщения и отправка ответа пользователю

    :param data: JSON с данными о входящем сообщении
    """
    try:
        direction = data['event']['message']['direction']
        # Здесь мы устанавливаем триггер только на входящие сообщения
        if direction == 'inbound':
            chat_id = data['event']['chat_id']
            user_prompt = data['event']['message']['text']['text']
            print("Получили сообщение от пользователя: ", user_prompt)

            # Здесь мы отправляем сообщение Ассистенту
            response_text, thread_id = await AssistantResponse.get_response(user_prompt=user_prompt)
            print(f"Получил сообщение от ассистента: ", response_text)

            # Здесь мы отправляем ответ пользователю
            await RadistOnlineConnect.send_message(chat_id, response_text)
            print(f"Ответ пользователю отправлен!")
    except KeyError:
        print(data)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000)
