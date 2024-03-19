from instructor import llm_validator
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, BeforeValidator
from typing import Optional, Annotated

from src.core.config import openai_clients
from src.core.texts import SurveyConfirmationTexts, SurveyInitialCheckTexts, SurveyFullCheckTexts

instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class SurveyConfirmation(BaseModel):
    """
    Это инструктор по проверке ответа пользователя с подтверждением заполненности анкеты
    """
    confirmation: bool = Field(description=SurveyConfirmationTexts.CONFIRMATION_DESCRIPTION)

    @staticmethod
    async def get_survey_confirmation(message_text) -> bool:
        """
        Функция для обработки входящего сообщения с подтверждением (шаг 1.0)
        :param message_text: текст сообщения
        :return: True/False
        """
        get_survey_confirmation: SurveyConfirmation = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=SurveyConfirmation,
            max_retries=2,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return get_survey_confirmation.confirmation


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


class SurveyFullCheck(BaseModel):
    """
    Это инструктор по полной проверке анкеты пользователей в первом шаге клиента с нейроменеджером
    """
    city: Optional[str] = Field(description=SurveyFullCheckTexts.CITY_TEXT)
    name: Optional[str] = Field(description=SurveyFullCheckTexts.NAME_TEXT)
    age: Optional[str] = Field(description=SurveyFullCheckTexts.BABY_AGE_TEXT)
    problem: Optional[str] = Field(description=SurveyFullCheckTexts.PROBLEM_TEXT)
    neurologist_observation: Optional[str] = Field(description=SurveyFullCheckTexts.NEUROLOGY_TEXT)

    @field_validator("age")
    def parse_age(cls, value):  # noqa
        if isinstance(value, int):
            return value
        try:
            birthday = datetime.strptime(value, "%Y-%m-%d")
            return birthday
        except (ValueError, TypeError):
            print("Эти данные я не смог обработать:", value)
            return None

    @staticmethod
    async def get_survey_full_check(message_text):
        """
        Функция для обработки сообщения пользователя для извлечения необходимых данных
        :param message_text: Текст сообщения пользователя в Whatsapp
        :return: результат проверки в виде 5ти параметров: city, name, age, problem, neurologist_observation
        """
        survey_full_check: SurveyFullCheck = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=SurveyFullCheck,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": message_text
                },
            ],
        )
        return survey_full_check
