import ast

from instructor import llm_validator
from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, Field, field_validator, BeforeValidator

from src.core.config import openai_clients
from src.core.texts import ObjectionsCheckerTexts, SurveyInitialCheckTexts

instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class JSONChecker(BaseModel):
    json_dict: Optional[dict] = Field(description=ObjectionsCheckerTexts.IS_JSON_DESCRIPTION)

    @field_validator("json_dict")
    def json_validator(cls, value):  # noqa
        if isinstance(value, str):
            return ast.literal_eval(value)

        if isinstance(value, dict) or isinstance(value, bool):
            return value

    @staticmethod
    async def check_json(message_text: str):
        message_text: JSONChecker = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=JSONChecker,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.json_dict


class SendImageChecker(BaseModel):
    need_send_image: bool = Field(description=ObjectionsCheckerTexts.SEND_IMAGE_DESCRIPTION)

    @staticmethod
    async def send_image(message_text: str):
        message_text: SendImageChecker = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=SendImageChecker,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.need_send_image


class SendZoomImageChecker(BaseModel):
    need_send_zoom_image: bool = Field(description=ObjectionsCheckerTexts.SEND_ZOOM_IMAGE_DESCRIPTION)

    @staticmethod
    async def send_zoom_image(message_text: str):
        message_text: SendZoomImageChecker = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=SendZoomImageChecker,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.need_send_zoom_image


class SurveyInitialCheck(BaseModel):
    """
    Это инструктор по первичной проверке анкеты пользователя (если анкета заполнена)
    """
    baby_age: Optional[str] = Field(
        description=SurveyInitialCheckTexts.BABY_AGE_TEXT
    )
    segment: Annotated[str, BeforeValidator(llm_validator(
        statement=SurveyInitialCheckTexts.SEGMENT_STATEMENT_TEXT,
        openai_client=instructor_client,
        model='gpt-4-turbo-preview'
    ))] = Field(
        description=SurveyInitialCheckTexts.SEGMENT_TEXT
    )
    for_online: bool = Field(
        description=SurveyInitialCheckTexts.FOR_ONLINE_TEXT
    )

    @field_validator("baby_age")
    def parse_age(cls, value):  # noqa
        if isinstance(value, int):
            return value
        try:
            birthday = datetime.strptime(value, "%Y-%m-%d")
            today = datetime.now()
            difference = (today.year - birthday.year) * 12 + today.month - birthday.month
            return difference
        except (ValueError, TypeError):
            return None

    @staticmethod
    async def get_survey_initial_check(survey_data: dict):
        """
        Функция для обработки данных по анкете пользователя для проверки на валидность
        :param survey_data: dict со значениями для проверки
        :return: результат проверки в виде 3-х параметров: baby_age, segment, for_online
        """
        answer_str = ', '.join(f"{key}: {value}" for key, value in survey_data.items())
        survey_initial_check: SurveyInitialCheck = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=SurveyInitialCheck,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": answer_str
                },
            ],
        )
        return survey_initial_check.baby_age, survey_initial_check.segment, survey_initial_check.for_online


class GetSlotId(BaseModel):
    """Инструктор нужен для получения ID слота из сообщения ассистента"""
    slot_id: str = Field(description="получи из текста ID слота")

    @staticmethod
    async def get_slot_id(message_text: str):
        message_text: GetSlotId = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=GetSlotId,
            max_retries=2,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.slot_id
