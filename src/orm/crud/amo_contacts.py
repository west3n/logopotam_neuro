import asyncio

from sqlalchemy import select

from src.orm.session import get_session
from src.orm.models.amo_contacts import AmoContacts


class AmoContactsCRUD:
    """
    Здесь располагаются методы взаимодействия с таблицей amo_contacts
    """
    @staticmethod
    async def check_contact_by_phone(phone_number):
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                contact = select(AmoContacts).where(AmoContacts.phone == phone_number)
        return contact is not None


if __name__ == '__main__':
    asyncio.run(AmoContactsCRUD.check_contact_by_phone('5555555555'))
