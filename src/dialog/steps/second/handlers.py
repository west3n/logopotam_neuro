from src.api.amoCRM.leads import LeadFetcher
from src.api.radistonline.messages import RadistonlineMessages

from src.core.texts import SecondStepTexts
from src.core.config import settings

from src.dialog.steps.second.llm_instructor import StepTwoCheck

from src.orm.crud.radist_chats import ChatStepsCRUD


async def step_2_0_handler(messages_text: str, chat_id: int, lead_id: int):
    check = await StepTwoCheck.get_step_two_check(messages_text)
    if not check:
        await ChatStepsCRUD.update(chat_id, "COMPLETE")
        await LeadFetcher.change_lead_status(
            lead_id=lead_id,
            status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР'
        )
    else:
        await ChatStepsCRUD.update(chat_id, "COMPLETE")
        await RadistonlineMessages.send_message(
            chat_id=chat_id,
            text=SecondStepTexts.MESSAGE_TEXT_TRUE
        )
        await RadistonlineMessages.send_image(
            chat_id=chat_id,
            image_url=settings.ZOOM_IMAGE_URL
        )
        await LeadFetcher.change_lead_status(
            lead_id=lead_id,
            status_name='ТРЕБУЕТСЯ МЕНЕДЖЕР'
        )
