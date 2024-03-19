import asyncio
import uuid
from datetime import datetime

from openai import BadRequestError

from src.core.config import settings, openai_clients

from src.orm.crud.radist_chats import RadistChatsCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD

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
    async def get_response(chat_id: int, user_prompt: str):
        """
        Здесь описана логика получения ответа от ассистента, в случае большого количества одновременных запросов,
        ассистент откладывает ответы в очередь и отвечает в порядке очереди, избегая возникновения ошибок

        :param chat_id: ID чата для сохранения нового Thread ID
        :param user_prompt: Текст сообщения от пользователя
        :return: new_message - сообщение от ассистента и thread_id - ID треда для записи в БД, если отсутствовал
        """
        # Получаем thread_id из БД пользователя, если отсутствует, создаём новый и сохраняем
        thread_id = await RadistChatsCRUD.get_thread_id(chat_id)
        if not thread_id:
            thread_id = await Assistant.create_thread()
            await RadistChatsCRUD.save_new_thread(chat_id, thread_id)
        while True:
            try:
                # Создаём новую задачу в указанном thread_id
                await openai_client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=user_prompt,
                )
                run = await openai_client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=settings.OPENAI_ASSISTANT_ID
                )
                # Раз в секунду проверяем статус
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
                    data = {
                        "event": {
                            "chat_id": chat_id,
                            "message": {
                                "message_id": str(uuid.uuid4()),
                                "direction": "outbound",
                                "created_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
                                "text": {
                                    "text": new_message
                                }
                            },
                        }
                    }
                    await RadistMessagesCRUD.save_new_message(data)
                    return new_message
            except BadRequestError:
                await asyncio.sleep(5)
