import asyncio
from datetime import datetime
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
            async with session.begin():
                result = await session.execute(
                    select(func.count()).where(and_(
                        RadistMessages.chat_id == data['event']['chat_id'], RadistMessages.status == 'unanswered',
                        RadistMessages.sender != 'robot'
                    ))
                )
                count = result.scalar()
            return count

    @staticmethod
    async def get_all_unanswered_messages(chat_id: int):
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(RadistMessages.message_id, RadistMessages.text).where(
                        and_(RadistMessages.chat_id == chat_id, RadistMessages.status == 'unanswered',
                             RadistMessages.sender != 'robot'
                             )
                    )
                )
                messages = result.fetchall()
                return messages

    @staticmethod
    async def change_status(message_id: str, new_status: str):
        """
        Асинхронная функция для изменения статуса сообщения
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                stmt = (update(RadistMessages).where(RadistMessages.message_id == message_id).values(status=new_status))
                await session.execute(stmt)
                await session.commit()

    @staticmethod
    async def get_last_robot_message_text(chat_id: int):
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(RadistMessages.text).where(
                        and_(RadistMessages.chat_id == chat_id, RadistMessages.sender == 'robot')
                    ).order_by(RadistMessages.send_time.desc()).limit(1)
                )
                message = result.fetchone()
                return message[0] if message else None
