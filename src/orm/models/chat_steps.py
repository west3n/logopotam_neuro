from sqlalchemy import Column, Integer, String, Text
from src.orm.session import BaseModel


class ChatSteps(BaseModel):
    """
    Модель для отслеживания шагов чата, для подгрузки в чат необходимого ассистента или модели с системным промптом
    """
    __tablename__ = "chat_steps"

    step_id = Column("step_id", Integer, primary_key=True)
    type = Column("type", String(20))
    assistant_id = Column("assistant_id", String(50))
    model_name = Column("model_name", String(50))
    model_system_prompt = Column("model_system_prompt", Text)
