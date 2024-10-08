from datetime import datetime, timedelta

from sqlalchemy import select, update, insert, delete

from src.api.bubulearn.slots import BubulearnSlotsFetcher
from src.core.config import logger
from src.orm.models.slots import Slots
from src.orm.session import get_session


class SlotsCRUD:
    @staticmethod
    async def read_slots(lead_id: int = None):
        """
        Получение слотов
        :return: слоты
        """
        async with get_session() as session:  # noqa
            slots = await session.execute(select(Slots))
            slots = slots.scalars().all()
            slot_list = [
                {
                    "weekday": slot.weekday,
                    "start_time": slot.start_time.strftime("%d.%m.%Y %H:%M"),
                } for slot in slots if not slot.is_busy
            ]
            slot_dict_str = str([
                {
                    "slot_id": slot.slot_id,
                    "weekday": slot.weekday,
                    "start_time": slot.start_time.strftime("%d.%m.%Y %H:%M"),
                } for slot in slots if not slot.is_busy
            ])
            if lead_id:
                logger.info(f"Вывод списка слотов для сделки {lead_id}: {slot_dict_str}")
            return slot_list, slot_dict_str

    @staticmethod
    async def update_slots():
        """
        Обновляет слоты в БД через информацию, полученную из API bubulearn раз в минуту
        """
        slots_data = await BubulearnSlotsFetcher.get_slots()
        async with get_session() as session:  # noqa

            # Получаем все текущие слоты для сравнения с новой информацией
            existing_slots = await session.execute(select(Slots))
            existing_slots = existing_slots.scalars().all()
            existing_slot_ids = {slot.slot_id for slot in existing_slots}
            slots_data_ids = {slot['slot_id'] for slot in slots_data}

            # Добавляем недостающие слоты и удаляем ненужные
            slots_to_add = [slot for slot in slots_data if slot['slot_id'] not in existing_slot_ids]
            slots_to_delete = [slot for slot in existing_slots if slot.slot_id not in slots_data_ids]
            for new_slot in slots_to_add:
                await session.execute(insert(Slots).values(**new_slot))
            for slot_to_delete in slots_to_delete:
                await session.execute(delete(Slots).where(Slots.slot_id == slot_to_delete.slot_id))

            # Получаем слоты с резервом и убираем резерв, если прошло более 10 минут
            existing_slots_with_reserve_time = [slot for slot in existing_slots if slot.reserve_time]
            slots_with_10_min_reserve_time = [slot for slot in existing_slots_with_reserve_time if
                                              slot.reserve_time < datetime.now() - timedelta(minutes=10)]
            for slot in slots_with_10_min_reserve_time:
                await session.execute(update(Slots).where(Slots.slot_id == slot.slot_id).values(
                    is_busy=False, reserve_time=None
                ))
            await session.commit()

    @staticmethod
    async def take_slot(slot_id: str):
        """
        Бронь слота
        :param slot_id: ID слота
        """
        async with get_session() as session:  # noqa
            await session.execute(update(Slots).where(Slots.slot_id == slot_id).values(  # noqa
                is_busy=True, reserve_time=datetime.now()))
            await session.commit()
