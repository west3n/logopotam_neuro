from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.types import TIMESTAMP

from src.orm.models.radist_chats import RadistChats
from src.orm.session import BaseModel


class RadistMessages(BaseModel):
    """
    Модель для отслеживания сообщений Radist.Online
    """
    __tablename__ = "radist_messages"

    message_id = Column("message_id", String(200), primary_key=True)
    chat_id = Column("chat_id", Integer, ForeignKey(RadistChats.chat_id)) # noqa
    sender = Column("sender", String(20))
    text = Column("text", Text)
    send_time = Column("send_time", type_=TIMESTAMP(timezone=True))
    status = (Column("status", String(20), default='unanswered'))
    delay_status = (Column("delay_status", String, nullable=True, default=None))
