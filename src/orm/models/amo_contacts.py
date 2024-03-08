from sqlalchemy import Column, Integer, String, Date
from src.orm.session import BaseModel


class AmoContacts(BaseModel):
    """
    Определяем поля модели контактов в amoCRM
    """
    __tablename__ = "amo_contacts"

    contact_id = Column("contact_id", Integer, primary_key=True)
    name = Column("name", String(200))
    phone = Column("phone", String(20))
    city = Column("city", String(100))
    child_name = Column("child_name", String(200))
    child_birth_date = Column("child_birth_date", Date)
    doctor_enquiry = Column("doctor_enquiry", String(200))
    diagnosis = Column("diagnosis", String(500))
    segment = Column("segment", String(1))

