from datetime import datetime, timedelta

from sqlalchemy import select, update, insert, delete

from src.api.bubulearn.slots import BubulearnSlotsFetcher
from src.core.config import logger
from src.orm.models.slots import Slots
from src.orm.session import get_session


class SlotsCRUD:
    @staticmethod
    async def read_slots():
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                slots = await session.execute(select(Slots))
                slots = slots.scalars().all()
                return str([
                    {
                        "weekday": slot.weekday,
                        "start_time": slot.start_time.strftime("%d.%m.%Y %H:%M"),
                    } for slot in slots if not slot.is_busy
                ]), str([
                    {
                        "slot_id": slot.slot_id,
                        "weekday": slot.weekday,
                        "start_time": slot.start_time.strftime("%d.%m.%Y %H:%M"),
                    } for slot in slots if not slot.is_busy
                ])

    @staticmethod
    async def update_slots():
        slots_data = await BubulearnSlotsFetcher.get_slots()
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                existing_slots = await session.execute(select(Slots))
                existing_slots = existing_slots.scalars().all()
                existing_slots_with_reserve_time = [slot for slot in existing_slots if slot.reserve_time]
                existing_slot_ids = {slot.slot_id for slot in existing_slots}
                slots_data_ids = {slot['slot_id'] for slot in slots_data}
                slots_to_add = [slot for slot in slots_data if slot['slot_id'] not in existing_slot_ids]
                slots_to_delete = [slot for slot in existing_slots if slot.slot_id not in slots_data_ids]
                for new_slot in slots_to_add:
                    await session.execute(insert(Slots).values(**new_slot))
                for slot_to_delete in slots_to_delete:
                    await session.execute(delete(Slots).where(Slots.slot_id == slot_to_delete.slot_id))
                slots_with_10_min_reserve_time = [slot for slot in existing_slots_with_reserve_time if slot.reserve_time < datetime.now() - timedelta(minutes=10)]
                for slot in slots_with_10_min_reserve_time:
                    await session.execute(update(Slots).where(Slots.slot_id == slot.slot_id).values(
                        is_busy=False, reserve_time=None
                    ))
                await session.commit()
                print("Слоты обновлены")
                logger.info("Слоты обновлены")

    @staticmethod
    async def take_slot(slot_id: str):
        async_session = await get_session()
        async with async_session() as session:
            async with session.begin():
                await session.execute(update(Slots).where(Slots.slot_id == slot_id).values(
                    is_busy=True, reserve_time=datetime.now()
                )
            )
                await session.commit()
