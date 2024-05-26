from datetime import datetime, timedelta
from typing import List

from sqlalchemy import select, update, and_
from sqlalchemy.dialects.postgresql import insert

from src.orm.models.amo_leads import AmoLeads
from src.orm.models.radist_chats import RadistChats
from src.orm.models.radist_messages import RadistMessages
from src.orm.session import get_session


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

    @staticmethod
    async def change_delay_status(chat_id: int, new_status: str):
        """
        Изменяем статус сообщений
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                stmt = (update(RadistMessages).where(RadistMessages.chat_id == chat_id).values(
                    delay_status=new_status))
                await session.execute(stmt)
                await session.commit()

    @staticmethod
    async def get_30_minutes_delay_chats():
        thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                query = session.query(
                    AmoLeads.lead_id,
                    AmoLeads.chat_id,
                    RadistChats.step
                ).distinct(
                    AmoLeads.lead_id,
                    AmoLeads.chat_id,
                    RadistChats.step
                ).join(
                    RadistMessages, AmoLeads.chat_id == RadistMessages.chat_id
                ).join(
                    RadistChats, AmoLeads.chat_id == RadistChats.chat_id
                ).filter(
                    RadistMessages.send_time < thirty_minutes_ago,
                    RadistMessages.delay_status == None,  # noqa
                    RadistMessages.sender == 'robot'
                )

                results = query.all()
                return results

    @staticmethod
    async def get_2hrs_delay_chats():
        two_hours_ago = datetime.utcnow() - timedelta(hours=2)
        async_session = await get_session()
        async with (async_session() as session):
            async with session.begin():
                query = session.query(
                    AmoLeads.lead_id,
                    AmoLeads.chat_id,
                    RadistChats.step
                ).distinct(
                    AmoLeads.lead_id,
                    AmoLeads.chat_id,
                    RadistChats.step
                ).join(
                    RadistMessages, AmoLeads.chat_id == RadistMessages.chat_id
                ).join(
                    RadistChats, AmoLeads.chat_id == RadistChats.chat_id
                ).filter(
                    RadistMessages.send_time < two_hours_ago,
                    RadistMessages.delay_status == '30m',
                    RadistMessages.sender == 'robot'
                )
                results = query.all()
                return results
