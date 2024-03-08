from sqlalchemy import Column, Integer, ForeignKey

from src.orm.models.amo_pipelines import AmoPipelines
from src.orm.models.amo_statuses import AmoStatuses
from src.orm.models.amo_contacts import AmoContacts
from src.orm.models.radist_chats import RadistChats

from src.orm.session import BaseModel


class AmoLeads(BaseModel):
    """
    Модель для отслеживания лидов в amoCRM
    """
    __tablename__ = "amo_leads"

    lead_id = Column("lead_id", Integer, primary_key=True)
    pipeline_id = Column("pipeline_id", Integer, ForeignKey(AmoPipelines.pipeline_id))
    status_id = Column("status_id", Integer, ForeignKey(AmoStatuses.status_id))
    contact_id = Column("contact_id", Integer, ForeignKey(AmoContacts.contact_id))
    chat_id = Column("chat_id", Integer, ForeignKey(RadistChats.chat_id))
