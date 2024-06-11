from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

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
    async def get_neuro_status_id(status_name: str):
        """
        Get ID of a status based on its name
        :param status_name: Name of the status
        :return: Status ID
        """
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                result = await session.execute(
                    select(AmoStatuses.status_id)
                    .where(AmoStatuses.name == status_name))  # noqa
                status_id = result.scalar()

                return status_id
