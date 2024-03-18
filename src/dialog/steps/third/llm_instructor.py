
from pydantic import BaseModel, Field


from src.core.config import openai_clients


instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class StepThreeCheck(BaseModel):
    """
    Эта модель анализирует нужна ли помощь при установке Зума
    """
    detail: bool = Field(
        description="Ты анализируешь ответ на вопрос: Мы проводим урок в программе ZOOM (Зум). Ранее пользовались этой программой или потребуется моя помощь с установкой?"
                    "Твоя задача вернуть True, если нужна помощь с установкой программы или"
                    "вернуть False, если помощь не нужна или пользователь уже имеет ZOOM "

    )

    @staticmethod
    async def get_step_three_check(text):
        """
        Получаем данные возраста, сегмента и
        :param text - текст сообщения для анализа моделью гпт
        :return: True/False
        """
        step_three_check: StepThreeCheck = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=StepThreeCheck,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": text
                },
            ],
        )
        return step_three_check.detail
