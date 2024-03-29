from typing import Optional, Annotated

from instructor import llm_validator
from pydantic import BaseModel, Field, BeforeValidator, field_validator

from src.core.config import openai_clients
from src.core.texts import ObjectionsCheckerTexts

instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class MessageCategoryChecker(BaseModel):
    """
    Данный инструктор будет проверять входящее сообщение на предмет наличия в нём вопросов, не соответствующих алгоритму
    """
    algorythm_type: Optional[str] = Field(description=ObjectionsCheckerTexts.ALGORYTHM_DESCRIPTION)
    assistant_type: Optional[str] = Field(description=ObjectionsCheckerTexts.ASSISTANT_DESCRIPTION)

    @field_validator("algorythm_type")
    def validate_assistant_type(cls, value):  # noqa
        return None if value not in ["name", "birthday", "city", "problem", "diagnosis", "zoom"] else value

    @staticmethod
    async def check_message_for_objection(message_text: str):
        message_text: MessageCategoryChecker = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=MessageCategoryChecker,
            max_retries=2,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.algorythm_type, message_text.assistant_type


class DialogFinishChecker(BaseModel):
    dialog_finish_type: Optional[str] = Field(description=ObjectionsCheckerTexts.DIALOG_FINISH_DESCRIPTION)
    send_image: bool = Field(description=ObjectionsCheckerTexts.SEND_IMAGE_DESCRIPTION)

    @field_validator("dialog_finish_type")
    def validate_dialog_finish_type(cls, value):  # noqa
        return None if value not in ['positive', 'negative'] else value

    @staticmethod
    async def check_dialog_finish(message_text: str):
        message_text: DialogFinishChecker = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=DialogFinishChecker,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.dialog_finish_type, message_text.send_image
