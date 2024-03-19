from sqlalchemy import select, update

from src.orm.session import get_session
from src.orm.models.radist_chats import RadistChats


class RadistChatsCRUD:
    """
    Здесь располагаются методы взаимодействия с таблицей amo_chats
    """
    @staticmethod
    async def chat_existence(chat_id: int):
        chat_id = int(chat_id) if type(chat_id) is str else chat_id
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(select(RadistChats).where(RadistChats.chat_id == chat_id)) # noqa
                chat = result.fetchone()
        return chat is not None

    @staticmethod
    async def get_thread_id(chat_id: int):
        chat_id = int(chat_id) if type(chat_id) is str else chat_id
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(select(RadistChats.thread_id).where(RadistChats.chat_id == chat_id))  # noqa
                thread_id = result.fetchone()
        return thread_id[0] if thread_id else None

    @staticmethod
    async def save_new_thread(chat_id: int, thread_id: str):
        chat_id = int(chat_id) if type(chat_id) is str else chat_id
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                await session.execute(
                    update(RadistChats).values(thread_id=thread_id).where(RadistChats.chat_id == chat_id)
                )
                await session.commit()


class ChatStepsCRUD:
    @staticmethod
    async def update(chat_id: int, step: str):
        """
        Функция для добавления нового шага в таблицу amo_chats или обновления существующей записи
        :param chat_id: ID чата
        :param step: Шаг чата
        """
        chat_id = int(chat_id) if type(chat_id) is str else chat_id
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                new_lead_step = update(RadistChats).values(step=step).where(RadistChats.chat_id == chat_id) # noqa
                await session.execute(new_lead_step)
                await session.commit()

    @staticmethod
    async def read(chat_id: int):
        """
        Получает значение шага чата по ID лида
        :param chat_id: ID чата
        :return: Значение шага чата
        """
        chat_id = int(chat_id) if type(chat_id) is str else chat_id
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(select(RadistChats.step).where(RadistChats.chat_id == chat_id)) # noqa
                chat_step = result.fetchone()
                return chat_step[0] if chat_step else None
