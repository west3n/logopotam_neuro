import pytz

from datetime import datetime, timedelta
from typing import List

from sqlalchemy import select, update, and_, func, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import aliased

from src.orm.models.amo_leads import AmoLeads
from src.orm.models.radist_chats import RadistChats
from src.orm.models.radist_messages import RadistMessages
from src.orm.session import get_session


class RadistMessagesCRUD:
    """
    Здесь будут расположены методы взаимодействия с таблицей radist_messages
    """

    @staticmethod
    async def save_new_message(data: dict, delay_status: str = None):
        async with get_session() as session:  # noqa
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
                    if delay_status:
                        new_message_insert_stmt = insert(RadistMessages).values(
                            message_id=data['event']['message']['message_id'],
                            chat_id=data['event']['chat_id'],
                            sender='robot' if data['event']['message']['direction'] == 'outbound' else 'user',
                            text=data['event']['message']['text']['text'],
                            send_time=send_time,
                            delay_status=delay_status
                        ).on_conflict_do_nothing(
                            index_elements=['message_id']
                        )
                    await session.execute(new_message_insert_stmt)
                    await session.commit()

                # Это исключение срабатывает только при попытке сохранить сообщение с картинкой
                except KeyError:
                    pass

    @staticmethod
    async def get_all_unanswered_messages(chat_id: int):
        async with get_session() as session:  # noqa
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
        async with get_session() as session:  # noqa
            stmt = (update(RadistMessages).where(RadistMessages.message_id.in_(message_ids)).values(  # noqa
                status=new_status))
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def get_10_minutes_delay_chats() -> List:
        """
        Возвращает список чатов, в которых с момента последнего сообщения от нейроменеджера прошло более 10 минут
        """
        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        async with get_session() as session:  # noqa
            LatestRadistMessages = aliased(RadistMessages)
            subquery = (
                select(
                    LatestRadistMessages.chat_id,
                    func.max(LatestRadistMessages.send_time).label('latest_send_time')
                )
                .group_by(LatestRadistMessages.chat_id).subquery()
            )
            query = (
                select(
                    AmoLeads.lead_id, AmoLeads.chat_id, RadistChats.step
                )
                .distinct()
                .join(
                    RadistMessages, AmoLeads.chat_id == RadistMessages.chat_id  # noqa
                )
                .join(
                    RadistChats, AmoLeads.chat_id == RadistChats.chat_id
                )
                .join(
                    subquery, (RadistMessages.chat_id == subquery.c.chat_id) & (
                            RadistMessages.send_time == subquery.c.latest_send_time)
                )
                .filter(
                    RadistMessages.send_time < ten_minutes_ago,
                    RadistMessages.sender == 'robot',
                    RadistChats.is_delay_message_sent == False
                )
            )

            result = await session.execute(query)
            results = result.all()
            return results

    @staticmethod
    async def get_15_minutes_delay_chats() -> List:
        """
        Возвращает список чатов, в которых с момента последнего сообщения от нейроменеджера прошло более 15 минут
        """
        # здесь 5 минут вместо 15, т.к 10 минут уже прошло от сообщения, отправленного после 10-минутного молчания
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        async with get_session() as session:  # noqa
            LatestRadistMessages = aliased(RadistMessages)
            subquery = (
                select(
                    LatestRadistMessages.chat_id,
                    func.max(LatestRadistMessages.send_time).label('latest_send_time')
                )
                .group_by(LatestRadistMessages.chat_id).subquery()
            )
            query = (
                select(
                    AmoLeads.lead_id, AmoLeads.chat_id, RadistChats.step
                )
                .distinct()
                .join(
                    RadistMessages, AmoLeads.chat_id == RadistMessages.chat_id  # noqa
                )
                .join(
                    RadistChats, AmoLeads.chat_id == RadistChats.chat_id
                )
                .join(
                    subquery, (RadistMessages.chat_id == subquery.c.chat_id) & (
                            RadistMessages.send_time == subquery.c.latest_send_time)
                )
                .filter(
                    RadistMessages.send_time < five_minutes_ago,
                    RadistMessages.sender == 'robot',
                    RadistChats.is_delay_message_sent == True
                )
            )

            result = await session.execute(query)
            results = result.all()
            return results

    @staticmethod
    async def delete_old_messages():
        timezone = pytz.UTC
        now = datetime.now(timezone)
        older_than = now - timedelta(hours=10)

        async with get_session() as session:  # noqa
            query = (
                delete(RadistMessages)
                .where(RadistMessages.send_time < older_than)  # noqa
            )
            await session.execute(query)
