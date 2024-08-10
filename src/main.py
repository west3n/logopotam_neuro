"""
Для реализации обработки вебхуков мы используем Quart, так как Radist.Online и amoCRM требует делать это асинхронным
методом, в котором необходимо в течение 2-3 секунд отвечать о принятии.
"""
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from quart import Quart, request, jsonify, Response

from src.dialog.distributors.amo_distributor import amo_data_processing
from src.dialog.distributors.radist_distributor import radist_data_processing

from src.core.scheduler import send_10_min_delay_messages, change_status_15_min_delay_messages
from src.orm.session import create_metadata
from src.orm.crud.slots import SlotsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD

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


@app.route('/show_logs')
async def show_logs():
    """
    Показывает логи
    :return: логи
    """
    log_file_path = '/script/logs/info.log'
    separator = '-' * 50

    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as log_file:
            log_content = log_file.read()

        log_entries = log_content.split(f'\n{separator}\n')
        filtered_entries = [entry for entry in log_entries if 'ERROR' not in entry]
        filtered_log_content = f'\n{separator}\n'.join(filtered_entries)

        return Response(filtered_log_content, mimetype='text/plain')
    else:
        return jsonify({"error": "Log file not found"}), 404


@app.before_serving
async def start_scheduler():
    """
    Запуск ежеминутных задач + запуск создания базы данных

    1. Удаление старых сообщений
    2. Обновление слотов
    3. Отправка сообщений при 10-минутном молчании
    4. Смена статусов сделок при 15-минутном молчании
    """

    # Создание базы данных
    await create_metadata()

    # Запуск ежеминутных задач
    scheduler = AsyncIOScheduler()
    scheduler.add_job(RadistMessagesCRUD.delete_old_messages, 'cron', hour=22)
    scheduler.add_job(SlotsCRUD.update_slots, 'interval', seconds=30)
    scheduler.add_job(send_10_min_delay_messages, 'interval', seconds=70, max_instances=1)
    scheduler.add_job(change_status_15_min_delay_messages, 'interval', seconds=60, max_instances=1)
    scheduler.start()


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=5000)
