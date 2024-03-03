"""
Для реализации обработки вебхуков мы используем Quart, так как Radist.Online требует делать это асинхронным
методом, в котором необходимо в течение 5 секунд отвечать о принятии.
"""

from quart import Quart, request, jsonify

app = Quart(__name__)


@app.route('/event', methods=['POST'])
async def event():
    """
    Так как обработка данных входящих сообщений от пользователей может происходить гораздо дольше 5 секунд,
    то мы каждую задачу добавляем в очередь и моментально отправляем ответ об успешном приёме данных.
    :return:
    """
    data = await request.get_json()
    app.add_background_task(data_processing, data)
    return jsonify(''), 200


async def data_processing(data):
    print(data)


if __name__ == '__main__':
    app.run()
