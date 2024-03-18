import asyncio

from openai import BadRequestError
from src.core.config import settings, openai_clients

openai_client = openai_clients.OPENAI_ASYNC_CLIENT


class Assistant:
    @staticmethod
    async def create_thread():
        """
        Получаем новый ID треда для общения с ассистентом
        :return: ID треда
        """
        thread = await openai_client.beta.threads.create()
        return thread.id

    @staticmethod
    async def get_response(user_prompt: str, thread_id: None):
        """
        Здесь описана логика получения ответа от ассистента, в случае большого количества одновременных запросов,
        ассистент откладывает ответы в очередь и отвечает в порядке очереди, избегая возникновения ошибок

        :param user_prompt: Текст сообщения от пользователя
        :param thread_id: ID треда пользователя, если None, то создаётся новый
        :return: new_message - сообщение от ассистента и thread_id - ID треда для записи в БД, если отсутствовал
        """
        if thread_id is None:
            thread_id = await Assistant.create_thread()
        while True:
            try:
                await openai_client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=user_prompt,
                )
                run = await openai_client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=settings.OPENAI_ASSISTANT_ID
                )
                while run.status != "completed":
                    await asyncio.sleep(1)
                    run = await openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                    if run.status in ["cancelling", "cancelled", "failed", "expired"]:
                        await openai_client.beta.threads.messages.create(
                            thread_id=thread_id,
                            role="user",
                            content=user_prompt,
                        )
                        run = await openai_client.beta.threads.runs.create(
                            thread_id=thread_id,
                            assistant_id=settings.OPENAI_ASSISTANT_ID
                        )
                messages = await openai_client.beta.threads.messages.list(thread_id=thread_id)
                new_message = messages.data[0].content[0].text.value
                if user_prompt == new_message:
                    continue
                else:
                    return new_message, thread_id
            except BadRequestError:
                await asyncio.sleep(5)
