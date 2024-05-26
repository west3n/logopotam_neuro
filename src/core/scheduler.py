from src.api.amoCRM.leads import LeadFetcher
from src.api.amoCRM.tags import TagsFetcher
from src.api.radistonline.messages import RadistonlineMessages

from src.core.texts import SchedulerTexts

from src.orm.crud.amo_statuses import AmoStatusesCRUD
from src.orm.crud.radist_messages import RadistMessagesCRUD


async def send_30_min_delay_messages():
    chats = await RadistMessagesCRUD.get_30_minutes_delay_chats()
    for lead_id, chat_id, step in chats:
        neuro_status_id = await AmoStatusesCRUD.get_neuro_status_id("СТАРТ НЕЙРО")
        amo_status = LeadFetcher.get_lead_status_id_by_lead_id(str(lead_id))
        if neuro_status_id == amo_status:
            survey_text = SchedulerTexts.SURVEY_30MIN_DELAY
            slots_text = SchedulerTexts.SLOTS_30MIN_DELAY
            message_text = survey_text if step == 'survey' else slots_text
            await RadistonlineMessages.send_message(int(chat_id), message_text)
            await RadistMessagesCRUD.change_delay_status(int(chat_id), '30min')


async def change_status_2hrs_delay_messages():
    chats = await RadistMessagesCRUD.get_2hrs_delay_chats()
    for lead_id, chat_id, step in chats:
        neuro_status_id = await AmoStatusesCRUD.get_neuro_status_id("СТАРТ НЕЙРО")
        amo_status = LeadFetcher.get_lead_status_id_by_lead_id(str(lead_id))
        if neuro_status_id == amo_status:
            await LeadFetcher.change_lead_status(int(lead_id), 'В работе ( не было звонка)')
            await RadistMessagesCRUD.change_delay_status(int(chat_id), '2hrs')
            if step == 'registration':
                await TagsFetcher.add_new_tag(str(lead_id), 'не было нужного слота')
