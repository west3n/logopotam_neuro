from sqlalchemy import Column, Integer, String, ForeignKey

from src.orm.models.chat_steps import ChatSteps
from src.orm.session import BaseModel


class RadistChats(BaseModel):
    """
    Модель для отслеживания чатов Radist.Online
    """
    __tablename__ = "radist_chats"

    chat_id = Column("chat_id", Integer, primary_key=True)
    step_id = Column("step_id", Integer, ForeignKey(ChatSteps.step_id)) # noqa
    thread_id = Column("thread_id", String(50))
