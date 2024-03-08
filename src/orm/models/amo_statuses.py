from sqlalchemy import Column, Integer, String, ForeignKey

from src.orm.models.amo_pipelines import AmoPipelines
from src.orm.session import BaseModel


class AmoStatuses(BaseModel):
    """
    Определяем поля модели статусов воронок в amoCRM
    """
    __tablename__ = "amo_statuses"

    status_id = Column("status_id", Integer, primary_key=True)
    pipeline_id = Column(Integer, ForeignKey(AmoPipelines.pipeline_id))
    name = Column("name", String(200))
