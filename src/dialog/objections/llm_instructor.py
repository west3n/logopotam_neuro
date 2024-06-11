import ast
import asyncio

import pandas as pd
from instructor import llm_validator
from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, Field, field_validator, BeforeValidator, root_validator

from src.core.config import openai_clients, logger
from src.core.texts import ObjectionsCheckerTexts, SurveyInitialCheckTexts, SlotsTexts

instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class JSONChecker(BaseModel):
    json_dict: dict = Field(description=ObjectionsCheckerTexts.IS_JSON_DESCRIPTION)

    @field_validator('json_dict')
    def json_validator(cls, values): # noqa
        json_dict = ast.literal_eval(values) if isinstance(values, str) else values
        new_dict = {}
        for key, value in json_dict.items():
            if key == 'Имя':
                new_dict["Имя ребёнка"] = value
            elif key == 'Дата Рождения':
                new_dict["Дата рождения"] = int(pd.to_datetime(value).timestamp())
            elif key == 'Город':
                new_dict["Страна/город"] = value
            elif key == 'Подробнее о запросе':
                new_dict["Подробнее о запросе"] = value
            elif key == 'Диагноз (если есть)':
                new_dict["Диагноз (если есть)"] = value
            else:
                new_dict[key] = value
        return new_dict

    @staticmethod
    async def inject_json(message_text: str):
        message_text: JSONChecker = await instructor_async_client.chat.completions.create(
            model="gpt-4o",
            response_model=JSONChecker,
            max_retries=15,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.json_dict


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
        model='gpt-4o'
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
        if isinstance(survey_data['Дата рождения'], int):
            # Convert from timestamp to date string
            survey_data['Дата рождения'] = datetime.fromtimestamp(survey_data['Дата рождения']).strftime('%Y-%m-%d')
        elif isinstance(survey_data['Дата рождения'], str):
            # Ensure the date string is in the correct format
            try:
                survey_data['Дата рождения'] = datetime.fromisoformat(survey_data['Дата рождения']).strftime('%Y-%m-%d')
            except ValueError as e:
                logger.error(f"Ошибка в формате даты рождения: {e}. Анкета: {str(survey_data)}")

        answer_str = ', '.join(f"{key}: {value}" for key, value in survey_data.items())
        survey_initial_check: SurveyInitialCheck = await instructor_async_client.chat.completions.create(
            model="gpt-4o",
            response_model=SurveyInitialCheck,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": answer_str
                },
            ],
        )
        baby_age = 43 if not survey_initial_check.baby_age else survey_initial_check.baby_age
        return baby_age, survey_initial_check.segment, survey_initial_check.for_online


class GetSlotId(BaseModel):
    """Инструктор нужен для получения ID слота из сообщения ассистента"""
    slot_id: str = Field(description=asyncio.run(SlotsTexts.slot_validation_text()))

    @field_validator("slot_id")
    def not_none(cls, value):  # noqa
        if value is None:
            raise ValueError
        return value

    @staticmethod
    async def get_slot_id(message_text: str):
        message_text: GetSlotId = await instructor_async_client.chat.completions.create(
            model="gpt-4o",
            response_model=GetSlotId,
            max_retries=15,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return message_text.slot_id
