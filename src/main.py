"""
Для реализации обработки вебхуков мы используем Quart, так как Radist.Online и amoCRM требует делать это асинхронным
методом, в котором необходимо в течение 2-3 секунд отвечать о принятии.
"""

from quart import Quart, request, jsonify

from dialog.distributors.amo_distributor import amo_data_processing
from dialog.distributors.radist_distributor import radist_data_processing

app = Quart(__name__)


# Здесь отлавливаются события из Radist.Online (входящие / исходящие сообщения)
@app.route('/radist', methods=['POST'])
async def radist():
    """
    Так как обработка данных входящих сообщений от пользователей может происходить гораздо дольше 2-3 секунд,
    то мы каждую задачу добавляем в очередь и моментально отправляем ответ об успешном приёме данных.
    :return: 200
    """
    data = await request.get_json()

    # Отправляем задачу в фоновый процесс - распределитель и сразу отдаём ответ 200
    app.add_background_task(radist_data_processing, data)
    return jsonify(''), 200


# Здесь отлавливаются события из amoCRM (создание новой сделки и смена статуса сделки)
@app.route('/amocrm', methods=["POST"])
async def amocrm():
    """
    Так как обработка данных входящих сообщений от пользователей может происходить гораздо дольше 2-3 секунд,
    то мы каждую задачу добавляем в очередь и моментально отправляем ответ об успешном приёме данных.
    :return: 200
    """
    data = await request.form

    # Отправляем задачу в фоновый процесс - распределитель и сразу отдаём ответ 200
    app.add_background_task(amo_data_processing, data)
    return jsonify(''), 200


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000)
