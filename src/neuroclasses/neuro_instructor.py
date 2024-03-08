import asyncio

from instructor import llm_validator
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, BeforeValidator
from typing import Optional, Annotated

from src.core.config import openai_clients
from src.core.texts import SurveyInitialCheckTexts


instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class SurveyInitialCheck(BaseModel):
    """
    Это инструктор по первичной проверке анкеты пользователя.
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
        Получаем
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


if __name__ == '__main__':
    baby_age, segment, for_online = asyncio.run(SurveyInitialCheck.get_survey_initial_check(
        {
            'Имя ребёнка': 'Ирина',
            'Дата рождения': '29.04.2020',
            'Страна/город': 'Санкт-Петербург',
            'Подробнее о запросе': 'некоторые буквы и слова плохо проговаривает',
            'Диагноз(если есть)': 'Нет'
        }
    ))
    print(baby_age, segment, for_online)
