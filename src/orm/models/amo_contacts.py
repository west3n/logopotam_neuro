from sqlalchemy import Column, Integer, String, Boolean
from src.orm.session import BaseModel


class AmoContacts(BaseModel):
    """
    Определяем поля модели контактов в amoCRM
    """
    __tablename__ = "amo_contacts"

    contact_id = Column("contact_id", Integer, primary_key=True)
    name = Column("name", String(200))
    phone = Column("phone", String(20))
    is_renamed = Column("is_renamed", Boolean, default=False)
