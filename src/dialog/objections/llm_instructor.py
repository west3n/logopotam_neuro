from typing import Optional

from pydantic import BaseModel, Field

from src.core.config import openai_clients
from src.core.texts import ObjectionsCheckerTexts

instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class MessageCategoryChecker(BaseModel):
    """
    Данный инструктор будет проверять входящее сообщение на предмет наличия в нём вопросов, не соответствующих алгоритму
    """
    algorythm_type: Optional[str] = Field(description=ObjectionsCheckerTexts.ALGORYTHM_DESCRIPTION)
    complain_type: Optional[str] = Field(description=ObjectionsCheckerTexts.COMPLAIN_DESCRIPTION)
    assistant_type: Optional[str] = Field(description=ObjectionsCheckerTexts.ASSISTANT_DESCRIPTION)

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
        return message_text.algorythm_type, message_text.assistant_type, message_text.complain_type


class DialogFinishChecker(BaseModel):
    dialog_finish: bool = Field(description=ObjectionsCheckerTexts.DIALOG_FINISH_DESCRIPTION)
    send_image: bool = Field(description=ObjectionsCheckerTexts.SEND_IMAGE_DESCRIPTION)

    @staticmethod
    async def check_dialog_finish(message_text: str):
        message_text: DialogFinishChecker = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=DialogFinishChecker,
            max_retries=2,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.dialog_finish, message_text.send_image
