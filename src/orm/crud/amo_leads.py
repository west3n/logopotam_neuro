from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.orm.session import get_session

from src.orm.models.amo_contacts import AmoContacts
from src.orm.models.amo_leads import AmoLeads


class AmoLeadsCRUD:
    """
    Здесь располагаются методы взаимодействия с таблицей amo_leads
    """
    @staticmethod
    async def save_new_lead(lead_data):
        """
        Сохраняем новую сделку, получив необходимые данные из переданного словаря
        :param lead_data: dict с данными о новой сделке
        """
        lead_id = lead_data['id']
        pipeline_id = lead_data['pipeline_id']
        status_id = lead_data['status_id']
        contact_id = lead_data['_embedded']['contacts'][0]['id']

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
                    contact_id=contact_id
                )
                contact_do_nothing_stmt = contact_insert_stmt.on_conflict_do_nothing(
                    index_elements=['contact_id']
                )
                await session.execute(contact_do_nothing_stmt)
                await session.execute(lead_insert_stmt)
            await session.commit()

    @staticmethod
    async def change_lead_status(lead_id: int, status_id: int):
        """
        Здесь мы меняем статус задачи в БД
        :param lead_id: ID задачи
        :param status_id: ID нового статуса
        :return:
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                lead = await session.execute(select(AmoLeads).where(AmoLeads.lead_id == lead_id))
                lead = lead.scalar()
                if lead:
                    lead.status_id = status_id
            await session.commit()
