from sqlalchemy import select, update

from src.orm.session import get_session
from src.orm.models.amo_contacts import AmoContacts


class AmoContactsCRUD:
    """
    Здесь располагаются методы взаимодействия с таблицей amo_contacts
    """

    @staticmethod
    async def get_renamed_contact(contact_id: int):
        async with get_session() as session:  # noqa
            result = await session.execute(
                select(AmoContacts).where(
                    AmoContacts.contact_id == contact_id).filter(AmoContacts.is_renamed == False)  # noqa
            )  # noqa
            contact: AmoContacts = result.fetchone()
            return contact[0].name if contact else None

    @staticmethod
    async def changed_renamed_status(contact_id: int):
        async with get_session() as session:  # noqa
            await session.execute(
                update(AmoContacts).where(AmoContacts.contact_id == contact_id).values(  # noqa
                    is_renamed=True
                )
            )
            await session.commit()
