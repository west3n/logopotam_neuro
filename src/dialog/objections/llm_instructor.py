from pydantic import BaseModel, Field

from src.core.config import openai_clients
from src.core.texts import ObjectionsCheckerTexts

instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class ObjectionsChecker(BaseModel):
    """
    Данный инструктор будет проверять входящее сообщение на предмет наличия в нём вопросов, не соответствующих алгоритму
    """
    is_objection: bool = Field(description=ObjectionsCheckerTexts.OBJECTION_DESCRIPTION)
    category: str = Field(description=ObjectionsCheckerTexts.CATEGORY_DESCRIPTION)

    @staticmethod
    async def check_message_for_objection(message_text: str):
        message_text: ObjectionsChecker = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=ObjectionsChecker,
            max_retries=2,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.is_objection, message_text.category
