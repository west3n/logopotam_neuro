import asyncio
from typing import Union, List

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.orm.session import get_session

from src.orm.models.amo_contacts import AmoContacts
from src.orm.models.amo_leads import AmoLeads
from src.orm.models.radist_chats import RadistChats


class AmoLeadsCRUD:
    """
    Здесь располагаются методы взаимодействия с таблицей amo_leads
    """

    @staticmethod
    async def save_new_lead(lead_data, contact_data):
        """
        Сохраняем новую сделку, получив необходимые данные из переданных словарей
        :param lead_data: dict с данными о новой сделке
        :param contact_data: dict с данными о контакте новой сделки
        """
        lead_id = lead_data['id']
        pipeline_id = lead_data['pipeline_id']
        status_id = lead_data['status_id']
        contact_id = contact_data['id']
        contact_name = contact_data['name']
        contact_phone_number = contact_data['custom_fields_values'][0]['values'][0]['value']

        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                lead_insert_stmt = insert(AmoLeads).values(
                    lead_id=lead_id,
                    pipeline_id=pipeline_id,
                    status_id=status_id,
                    contact_id=contact_id
                )
                contact_insert_stmt = insert(AmoContacts).values(
                    contact_id=contact_id,
                    name=contact_name,
                    phone=contact_phone_number
                )
                contact_do_nothing_stmt = contact_insert_stmt.on_conflict_do_nothing(
                    index_elements=['contact_id']
                )
                await session.execute(contact_do_nothing_stmt)
                await session.execute(lead_insert_stmt)
            await session.commit()

    @staticmethod
    async def get_lead_by_id(lead_id: int):
        """
        Проверка наличия сделки в БД
        :param lead_id: ID сделки
        :return: True/False в зависимости от наличия/отсутствия сделки
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(select(AmoLeads).where(AmoLeads.lead_id == lead_id))
                lead = result.fetchone()
                return lead is not None

    @staticmethod
    async def save_new_chat_id(lead_id: int, chat_id: int):
        """
        Сохраняем chat_id для новой сделки
        :param lead_id: ID сделки
        :param chat_id: ID чата
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                chat_id_insert_stmt = insert(RadistChats).values(
                    chat_id=chat_id
                )
                chat_id_do_nothing_stmt = chat_id_insert_stmt.on_conflict_do_nothing(
                    index_elements=['chat_id']
                )
                await session.execute(chat_id_do_nothing_stmt)
                lead = await session.execute(select(AmoLeads).where(AmoLeads.lead_id == lead_id))  # noqa
                lead = lead.scalar()
                if lead:
                    lead.chat_id = chat_id
            await session.commit()

    @staticmethod
    async def change_lead_status(lead_id: int, status_id: int):
        """
        Здесь мы меняем статус сделки в БД
        :param lead_id: ID сделки
        :param status_id: ID нового статуса
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                lead = await session.execute(select(AmoLeads).where(AmoLeads.lead_id == lead_id))  # noqa
                lead = lead.scalar()
                if lead:
                    lead.status_id = status_id
            await session.commit()

    @staticmethod
    async def get_value_by_chat_id(chat_id: int, column: Union[str, List[str]]):
        """
        Здесь мы получаем значение указанного столбца у определённого chat_id
        :param chat_id: ID чата
        :param column: Имя столбца или список имен столбцов, значения которых нужно получить
        :return: Значение указанного столбца или список значений
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                if isinstance(column, str):
                    # Если column - строка, то выполняем запрос для одного столбца
                    result = await session.execute(select(getattr(AmoLeads, column)).where(AmoLeads.chat_id == chat_id))
                    value = result.fetchone()
                    return value[0] if value else None
                elif isinstance(column, list):
                    # Если column - список, то выполняем запрос для всех столбцов из списка
                    select_columns = [getattr(AmoLeads, col) for col in column]
                    result = await session.execute(select(*select_columns).where(AmoLeads.chat_id == chat_id))
                    values = result.fetchall()
                    return values[0] if values else None
