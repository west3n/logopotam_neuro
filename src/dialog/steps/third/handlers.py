from src.api.amoCRM.leads import LeadFetcher
from src.core.texts import ThirdStepTexts
from src.dialog.steps.third.llm_instructor import StepThreeCheck

from src.api.radistonline.messages import RadistonlineMessages
from src.orm.crud.chat_steps import ChatStepsCRUD


async def third_step_handler(messages_text: str, chat_id: int, lead_id: int):
    check = await StepThreeCheck.get_step_three_check(messages_text)
    if not check:
        await ChatStepsCRUD.update(lead_id, "CANCEL")
        await LeadFetcher.change_lead_status(
            lead_id=lead_id,
            status_name='Требуется менеджер'
        )
    else:
        await ChatStepsCRUD.update(lead_id, "CANCEL")
        await RadistonlineMessages.send_message(
            chat_id=chat_id,
            text=ThirdStepTexts.MESSAGE_TEXT_TRUE
        )
        await LeadFetcher.change_lead_status(
            lead_id=lead_id,
            status_name='Требуется менеджер'
        )