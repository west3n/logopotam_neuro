from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime

from src.orm.models.radist_chats import RadistChats
from src.orm.session import BaseModel


class RadistMessages(BaseModel):
    """
    Модель для отслеживания сообщений Radist.Online
    """
    __tablename__ = "radist_messages"

    message_id = Column("message_id", Integer, primary_key=True)
    chat_id = Column("chat_id", Integer, ForeignKey(RadistChats.chat_id)) # noqa
    sender = Column("sender", String(20))
    text = Column("text", Text)
    send_time = Column("send_time", DateTime)
