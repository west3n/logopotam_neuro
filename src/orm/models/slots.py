from sqlalchemy import Column, String, Boolean, DateTime

from src.orm.session import BaseModel


class Slots(BaseModel):
    __tablename__ = "slots"

    slot_id = Column("slot_id", String(200), primary_key=True)
    weekday = Column("weekday", String(20))
    start_time = Column("start_time", DateTime)
    is_busy = Column("is_busy", Boolean, default=False)
    reserve_time = Column("reserve_time", DateTime, nullable=True)
