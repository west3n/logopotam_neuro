from src.api.amoCRM.pipelines import PipelineFetcher
from src.orm.models.amo_pipeline import PipelineStatuses
from src.orm.session import get_session
from sqlalchemy.dialects.postgresql import insert


async def add_pipeline_statuses():
    pipeline_statuses_dict = await PipelineFetcher.get_pipeline_statuses()
    async_session = await get_session()
    async with async_session() as session:
        async with session.begin():
            for key, value in pipeline_statuses_dict.items():
                insert_stmt = insert(PipelineStatuses).values(id=key, name=value)
                do_nothing_stmt = insert_stmt.on_conflict_do_nothing(index_elements=['id'])
                await session.execute(do_nothing_stmt)
            await session.commit()
