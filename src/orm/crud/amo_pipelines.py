from sqlalchemy.dialects.postgresql import insert

from src.orm.session import get_session
from src.orm.models.amo_pipelines import AmoPipelines

from src.api.amoCRM.pipelines import PipelineFetcher


class AmoPipelinesCRUD:
    """
    Здесь будут расположены методы взаимодействия с таблицей amo_pipelines
    """

    @staticmethod
    async def create_all_pipelines():
        """
        Здесь мы создаём все воронки в базе данных на основе данных из amoCRM
        """
        all_pipelines = await PipelineFetcher.get_pipelines()
        for pipeline_data in all_pipelines:
            async with get_session() as session: # noqa
                pipeline_insert_stmt = insert(AmoPipelines).values(
                    pipeline_id=pipeline_data['id'],
                    name=pipeline_data['name']
                )
                pipeline_do_nothing_stmt = pipeline_insert_stmt.on_conflict_do_nothing(
                    index_elements=['pipeline_id']
                )
                await session.execute(pipeline_do_nothing_stmt)
                await session.commit()
