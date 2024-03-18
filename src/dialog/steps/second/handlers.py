from src.api.amoCRM.leads import LeadFetcher
from src.core.texts import SecondStepTexts
from src.dialog.steps.second.llm_instructor import StepTwoCheck, StepTwoOneCheck

from src.api.radistonline.messages import RadistonlineMessages
from src.orm.crud.chat_steps import ChatStepsCRUD


async def second_step_handler(messages_text: str, chat_id: int, lead_id: int):
    check = await StepTwoCheck.get_step_two_check(messages_text)
    if not check:
        await ChatStepsCRUD.update(lead_id, "3.0")
        await RadistonlineMessages.send_message(
            chat_id=chat_id,
            text=SecondStepTexts.SECOND_MESSAGE_TEXT_FALSE
        )

    else:
        await ChatStepsCRUD.update(lead_id, "2.1")
        await RadistonlineMessages.send_message(
            chat_id=chat_id,
            text=SecondStepTexts.SECOND_MESSAGE_TEXT_TRUE
        )


async def second_one_step_handler(messages_text: str, chat_id: int, lead_id: int):
    check = await StepTwoOneCheck.get_step_two_one_check(messages_text)
    print(check)
    if not check:
        await ChatStepsCRUD.update(lead_id, "CANCEL")
        await RadistonlineMessages.send_message(
            chat_id=chat_id,
            text=SecondStepTexts.SECOND_ONE_MESSAGE_TEXT_TRUE
        )
        await LeadFetcher.change_lead_status(
            lead_id=lead_id,
            status_name='Требуется менеджер'
        )

    else:
        await ChatStepsCRUD.update(lead_id, "3.0")
        await RadistonlineMessages.send_message(
            chat_id=chat_id,
            text=SecondStepTexts.SECOND_MESSAGE_TEXT_FALSE
        )
