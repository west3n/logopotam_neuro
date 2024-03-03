from sqlalchemy import Column, Integer, String

from src.orm.session import Base


class PipelineStatuses(Base):
    __tablename__ = 'pipeline_statuses'

    id = Column(Integer, primary_key=True)
    name = Column(String(250))
