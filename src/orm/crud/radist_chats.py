from sqlalchemy import select

from src.orm.session import get_session
from src.orm.models.radist_chats import RadistChats


class RadistChatsCRUD:
    """
    Здесь располагаются методы взаимодействия с таблицей amo_chats
    """
    @staticmethod
    async def chat_existence(chat_id):
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(select(RadistChats).where(RadistChats.chat_id == chat_id))
                chat = result.fetchone()
        return chat is not None
