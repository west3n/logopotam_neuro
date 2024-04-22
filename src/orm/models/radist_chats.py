from sqlalchemy import Column, Integer, String

from src.orm.session import BaseModel


class RadistChats(BaseModel):
    """
    Модель для отслеживания чатов Radist.Online
    """
    __tablename__ = "radist_chats"

    chat_id = Column("chat_id", Integer, primary_key=True)
    algorythm_thread_id = Column("thread_id", String(50))
    registration_thread_id = Column("registration_thread_id", String(50))
    step = Column("step", String(20))
