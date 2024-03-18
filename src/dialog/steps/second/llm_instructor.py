
from pydantic import BaseModel, Field


from src.core.config import openai_clients


instructor_client = openai_clients.OPENAI_INSTRUCTOR_CLIENT
instructor_async_client = openai_clients.OPENAI_ASYNC_INSTRUCTOR_CLIENT


class StepTwoCheck(BaseModel):
    """
    Эта модель смотрит сообщение юзера о лого-группе или логопеде у ребенка
    """
    detail: bool = Field(
        description="Ты анализируешь ответ на вопрос: Подскажите, пожалуйста, на данный момент ребенок занимается у логопеда/состоит в лого-группе?"
                    "Твоя задача вернуть True, если ответ родителя имеет в себе упоминание о том, что ребенок уже занимается с логопедом или в лого-группе или"
                    "вернуть False, если в ответе на вопрос отрицается занятия ребенка с логопедом или в логогруппе"

    )

    @staticmethod
    async def get_step_two_check(text):
        """
        Получаем данные возраста, сегмента и
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


class StepTwoOneCheck(BaseModel):
    """
    Эта модель смотрит сообщение юзера о текузем прогрессе ребенка в  лого-группе или логопеде
    """
    detail: bool = Field(
        description="Ты анализируешь ответ на вопрос: Подскажите, вас устраивает текущий прогресс от занятий или вы хотите сменить логопеда??"
                    "Твоя задача если в ответе явно указано, что прогресс устраивает - вернуть True. "
                    "Если в ответе родитель высказывает некоторые недовольства "
                    "от текущего прогресса или недоволен полностью или явно указано о том, что хотелось бы сменить логопеда или специалиста - вернуть False"

    )

    @staticmethod
    async def get_step_two_one_check(text):
        """
        Получаем данные возраста, сегмента и
        :param text - текст сообщения для анализа моделью гпт
        :return: True/False
        """
        step_two_check: StepTwoOneCheck = await instructor_async_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            response_model=StepTwoOneCheck,
            max_retries=5,
            messages=[
                {
                    "role": "user",
                    "content": text
                },
            ],
        )
        return step_two_check.detail