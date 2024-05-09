import asyncio
import pytz

from datetime import datetime, timedelta
from typing import List

from sqlalchemy import select, update, and_, func
from sqlalchemy.dialects.postgresql import insert

from src.orm.session import get_session
from src.orm.models.radist_messages import RadistMessages


class RadistMessagesCRUD:
    """
    Здесь будут расположены методы взаимодействия с таблицей radist_messages
    """

    @staticmethod
    async def save_new_message(data: dict):
        async_session = await get_session()
        async with async_session() as session:
            send_time = data['event']['message']['created_at']
            try:
                send_time = datetime.strptime(send_time, '%Y-%m-%dT%H:%M:%S%z')
            except ValueError:
                try:
                    send_time = datetime.strptime(send_time, '%Y-%m-%dT%H:%M:%S.%f%z')
                except ValueError:
                    send_time = datetime.strptime(send_time, '%Y-%m-%dT%H:%M:%S.%f')
            async with session.begin():
                try:
                    new_message_insert_stmt = insert(RadistMessages).values(
                        message_id=data['event']['message']['message_id'],
                        chat_id=data['event']['chat_id'],
                        sender='robot' if data['event']['message']['direction'] == 'outbound' else 'user',
                        text=data['event']['message']['text']['text'],
                        send_time=send_time
                    ).on_conflict_do_nothing(
                        index_elements=['message_id']
                    )
                    await session.execute(new_message_insert_stmt)
                    await session.commit()
                # This exception only works if we are trying to save an image
                except KeyError:
                    pass

    @staticmethod
    async def get_all_unanswered_messages(chat_id: int):
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(RadistMessages.message_id, RadistMessages.text)
                    .where(and_(
                        RadistMessages.chat_id == chat_id,
                        RadistMessages.status == 'unanswered',
                        RadistMessages.sender != 'robot'
                    ))
                )
                messages = result.fetchall()
            return messages

    @staticmethod
    async def change_status(message_ids: List[str], new_status: str):
        """
        Изменяем статус сообщений
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                stmt = (update(RadistMessages).where(RadistMessages.message_id.in_(message_ids)).values(
                    status=new_status))
                await session.execute(stmt)
                await session.commit()

    @staticmethod
    async def is_last_robot_message_old(chat_id: int):
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(RadistMessages.send_time)
                    .where(and_(
                        RadistMessages.chat_id == chat_id,
                        RadistMessages.sender == 'robot'
                    ))
                    .order_by(RadistMessages.send_time.desc())
                    .limit(1)
                )
                last_message_time = result.scalar_one_or_none()

                if last_message_time:
                    current_time = datetime.now()
                    time_difference = current_time - last_message_time

                    if time_difference > timedelta(hours=1):
                        return True
        return False
