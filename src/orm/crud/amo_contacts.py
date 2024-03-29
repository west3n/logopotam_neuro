from sqlalchemy import select, update

from src.orm.session import get_session
from src.orm.models.amo_contacts import AmoContacts


class AmoContactsCRUD:
    """
    Здесь располагаются методы взаимодействия с таблицей amo_contacts
    """
    @staticmethod
    async def update_contact_values(contact_id: int, update_columns: dict):
        """
        Обновляем параметры в таблице в зависимости от значения словаря
        :param contact_id: ID контакта
        :param update_columns: Словарь со значениями столбцов и значений
        :return:
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                field_mappings = {
                    "city": AmoContacts.city,
                    "child_name": AmoContacts.child_name,
                    "child_birth_date": AmoContacts.child_birth_date,
                    "doctor_enquiry": AmoContacts.doctor_enquiry,
                    "diagnosis": AmoContacts.diagnosis,
                    "segment": AmoContacts.segment,
                }
                await session.execute(update(AmoContacts).where(AmoContacts.contact_id == contact_id).values( # noqa
                    {field_mappings[key]: value for key, value in update_columns.items()})
                )
                await session.commit()

    @staticmethod
    async def get_contact_values(contact_id: int):
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                empty_fields = []
                result = await session.execute(select(
                    AmoContacts.child_name, AmoContacts.child_birth_date, AmoContacts.city, AmoContacts.diagnosis,
                    AmoContacts.doctor_enquiry).where(AmoContacts.contact_id == contact_id)) # noqa
                contact_values = result.fetchone()
                field_names = ["child_name", "child_birth_date", "city", "diagnosis", "doctor_enquiry"]
                field_values = dict(zip(field_names, contact_values))
                for field, value in field_values.items():
                    if not value:
                        empty_fields.append(field)
                return empty_fields, field_values
