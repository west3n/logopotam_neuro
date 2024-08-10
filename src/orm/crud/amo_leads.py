from typing import Union, List

from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert

from src.core.config import logger
from src.orm.models.radist_messages import RadistMessages
from src.orm.session import get_session

from src.orm.models.amo_contacts import AmoContacts
from src.orm.models.amo_leads import AmoLeads
from src.orm.models.radist_chats import RadistChats


class AmoLeadsCRUD:
    """
    Здесь располагаются методы взаимодействия с таблицей amo_leads
    """

    @staticmethod
    async def save_new_lead(lead_data, contact_data, phone_number):
        """
        Сохраняем новую сделку, получив необходимые данные из переданных словарей
        :param phone_number: Номер телефона новой сделки
        :param lead_data: dict с данными о новой сделке
        :param contact_data: dict с данными о контакте новой сделки
        """
        lead_id = lead_data['id']
        lead_name = lead_data['name']
        pipeline_id = lead_data['pipeline_id']
        status_id = lead_data['status_id']
        contact_id = contact_data['id']
        contact_name = contact_data['name']

        async with get_session() as session:  # noqa
            lead_insert_stmt = insert(AmoLeads).values(
                lead_id=lead_id,
                lead_name=lead_name,
                pipeline_id=pipeline_id,
                status_id=status_id,
                contact_id=contact_id
            )
            contact_insert_stmt = insert(AmoContacts).values(
                contact_id=contact_id,
                name=contact_name,
                phone=phone_number
            )
            contact_do_nothing_stmt = contact_insert_stmt.on_conflict_do_nothing(
                index_elements=['contact_id']
            )
            await session.execute(contact_do_nothing_stmt)
            await session.execute(lead_insert_stmt)
            await session.commit()

    @staticmethod
    async def get_lead_by_id(lead_id: int, renamed: bool = False):
        """
        Проверка наличия сделки в БД
        :param renamed: True, если нужен поиск по ID сделки с еще не переименованными контактами
        :param lead_id: ID сделки
        :return: True/False в зависимости от наличия/отсутствия сделки
        """
        async with get_session() as session:  # noqa
            if not renamed:
                result = await session.execute(select(AmoLeads).where(AmoLeads.lead_id == lead_id))  # noqa
            else:
                result = await session.execute(
                    select(AmoLeads).where(AmoLeads.lead_id == lead_id).filter(AmoLeads.is_renamed == False)  # noqa
                )
            lead: AmoLeads = result.fetchone()
            return lead[0].lead_name if lead else None

    @staticmethod
    async def get_lead_id_by_contact_id(contact_id: int):
        """
        Получение ID сделки по ID контакта
        :param contact_id: ID контакта
        :return: ID сделки
        """
        async with get_session() as session:  # noqa
            result = await session.execute(select(AmoLeads).where(AmoLeads.contact_id == contact_id))  # noqa
            lead: AmoLeads = result.fetchone()
            return lead[0].lead_id if lead else None

    @staticmethod
    async def save_new_chat_id(lead_id: int, chat_id: int):
        """
        Сохраняем chat_id для новой сделки
        :param lead_id: ID сделки
        :param chat_id: ID чата
        """
        async with get_session() as session:  # noqa
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
        async with get_session() as session:  # noqa
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
        async with get_session() as session:  # noqa
            if isinstance(column, str):
                # Если column - строка, то выполняем запрос для одного столбца
                result = await session.execute(
                    select(getattr(AmoLeads, column)).where(AmoLeads.chat_id == chat_id))  # noqa
                value = result.fetchone()
                return value[0] if value else None
            elif isinstance(column, list):
                # Если column - список, то выполняем запрос для всех столбцов из списка
                select_columns = [getattr(AmoLeads, col) for col in column]
                result = await session.execute(select(*select_columns).where(AmoLeads.chat_id == chat_id))  # noqa
                values = result.fetchall()
                return values[0] if values else None

    @staticmethod
    async def change_renamed_status(lead_id: int):
        """
        Здесь мы меняем статус сделки в БД
        :param lead_id: ID сделки
        """
        async with get_session() as session:  # noqa
            await session.execute(
                update(AmoLeads).where(AmoLeads.lead_id == lead_id).values(is_renamed=True))  # noqa
            await session.commit()

    @staticmethod
    async def update_lead_name(lead_id: int, lead_name: str):
        """
        Обновляем имя сделки
        :param lead_id: ID сделки
        :param lead_name: Новое имя сделки
        """
        async with get_session() as session:  # noqa
            await session.execute(
                update(AmoLeads).where(AmoLeads.lead_id == lead_id).values(lead_name=lead_name))  # noqa
            await session.commit()

    @staticmethod
    async def delete_lead_and_related_data(lead_id: int):
        """
        Удаляем сделку и все связанные с ней данные
        :param lead_id: ID сделки
        """
        async with get_session() as session: # noqa
            lead = await session.execute(select(AmoLeads).where(AmoLeads.lead_id == lead_id))  # noqa
            lead = lead.scalars().first()

            if not lead:
                return

            contact_id = lead.contact_id
            chat_id = lead.chat_id

            delete_messages = (
                delete(RadistMessages)
                .where(RadistMessages.chat_id == chat_id)
            )
            await session.execute(delete_messages)

            delete_lead = (
                delete(AmoLeads)
                .where(AmoLeads.lead_id == lead_id) # noqa
            )
            await session.execute(delete_lead)

            delete_chats = (
                delete(RadistChats)
                .where(RadistChats.chat_id == chat_id)
            )
            await session.execute(delete_chats)

            delete_contacts = (
                delete(AmoContacts)
                .where(AmoContacts.contact_id == contact_id)
            )
            await session.execute(delete_contacts)
            await session.commit()
            logger.info(f"Сделка с ID {lead_id} удалена из БД")
