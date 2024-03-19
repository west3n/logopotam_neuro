from pydantic import BaseModel, Field

from src.core.config import openai_clients
from src.core.texts import SecondStepTexts


instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class StepTwoCheck(BaseModel):
    """
    Этот инструктор анализирует, нужна ли помощь при установке ZOOM
    """
    detail: bool = Field(
        description=SecondStepTexts.INSTRUCTOR_DESCRIPTION_DETAIL
    )

    @staticmethod
    async def get_step_two_check(text):
        """
        Обрабатываем входящее сообщение пользователя в шаге 2.0
        :param text - текст сообщения для анализа моделью гпт
        :return: True/False
        """
        step_two_check: StepTwoCheck = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=StepTwoCheck,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": text
                },
            ],
        )
        return step_two_check.detail
