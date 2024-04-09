from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert

from src.orm.models.radist_messages import RadistMessages
from src.orm.session import get_session
from src.orm.models.amo_statuses import AmoStatuses

from src.api.amoCRM.pipelines import PipelineFetcher


class AmoStatusesCRUD:
    """
    Здесь будут расположены методы взаимодействия с таблицей amo_statuses
    """

    @staticmethod
    async def create_all_statuses():
        """
        Здесь мы создаём все статусы всех воронок в базе данных на основе данных из amoCRM
        """
        all_statuses = await PipelineFetcher.get_pipeline_statuses()

        for status_id, status_data in all_statuses.items():
            async_session = await get_session()
            async with async_session() as session:
                async with session.begin():
                    status_insert_stmt = insert(AmoStatuses).values(
                        status_id=status_id,
                        pipeline_id=status_data[0],
                        name=status_data[1]
                    )
                    status_do_nothing_stmt = status_insert_stmt.on_conflict_do_nothing(
                        index_elements=['status_id']
                    )
                    await session.execute(status_do_nothing_stmt)
                await session.commit()

    @staticmethod
    async def get_status_id_and_last_robot_message(status_name: str, chat_id: int):
        """
        Здесь мы получаем ID статуса по его имени
        :param chat_id: ID чата пользователя
        :param status_name: Имя статуса
        :return: ID статуса
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                # Get last robot message text
                result_message = await session.execute(
                    select(RadistMessages.text).where(
                        and_(RadistMessages.chat_id == chat_id, RadistMessages.sender == 'robot'))
                    .order_by(RadistMessages.send_time.desc()).limit(1)
                )
                result = result_message.fetchone()
                message_text = result[0] if result else None

                result_status = await session.execute(
                    select(AmoStatuses.status_id).where(AmoStatuses.name == status_name)) # noqa
                result = result_status.fetchone()
                status_id = result[0] if result else None

                return status_id, message_text
