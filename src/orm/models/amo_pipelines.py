from sqlalchemy import Column, Integer, String
from src.orm.session import BaseModel


class AmoPipelines(BaseModel):
    """
    Определяем поля модели воронок в amoCRM
    """
    __tablename__ = 'amo_pipelines'

    pipeline_id = Column('pipeline_id', Integer, primary_key=True)
    name = Column('name', String(200))
