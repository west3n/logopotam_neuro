import datetime

from src.orm.crud.slots import SlotsCRUD

now = datetime.datetime.now().strftime('%Y-%m-%d')


class SurveyInitialCheckTexts:
    BABY_AGE_TEXT: str = f"""Тебе нужно привести дату рождения из timestamp в такой вид: %Y-%m-%d."""

    SEGMENT_TEXT: str = """
    Если в сообщении указывается город,
    то возвращаешь только сегмент в виде буквы A, B или С в зависимости от города. A - это все крупные города России
    с населением более 250 тыс.человек, а также города-миллионники из всех развитых стран. B - это небольшие города
    России с населением от 100 до 250 тыс. человек, а также столицы стран СНГ, например, Минск или Астана. C - это
    деревни, сёла, очень маленькие города или любые города из экономически бедных стран."""

    SEGMENT_STATEMENT_TEXT: str = """Must contains one of these characters: A, B or C"""

    FOR_ONLINE_TEXT: str = """
    Возвращаешь исключительно True или False. False нужно вернуть в случае, если в разделе 
    Подробнее о запросе или Диагноз есть такие болезни:
    - Заикание
    - Логоневроз
    - Дисграфия
    - Дислексия
    - ЗПРР (задержка психоречевого развития)
    - ЗПР (задержка психического развития)
    - РАС (аутизм) любой формы, то есть Ребёнок повторяет все слова, но не понимает их смысл. Не отвечает на 
    вопросы взрослых. Сам не говорит, только повторяет, либо говорит, но не понимает + аутистические черты. 
    - Непроизвольное повторение слов (Эхолалия)
    - Дцп, лежачие дети, дети с тяжёлыми нарушениями моторики
    - Умственная отсталость любой степени тяжести
    - Дети с моторной алалией, апраксией (невозможностью совершать действия по подражанию или по заданию.)
    - Дети с эпилепсией (в активной и любой другой стадии)
    - ОНР (общее недоразвитие речи) 1 уровня
    - Синдром Дауна
    - Тугоухость любой стадии, глухота
    - Ринолалия (это искажение произносимых звуков из-за функционального нарушения или анатомических дефектов 
    речевого аппарата)
    - Расщелина твёрдого, мягкого небо.
    - Умственная отсталость любой степени тяжести
    - СДВГ (синдром дефицита внимания и гиперактивности)
    - Энцефалопатии любого типа (любое органическое поражение головного мозга)"""


class ObjectionsCheckerTexts:
    SEND_IMAGE_DESCRIPTION: str = """
    Только если в сообщении содержится словосочетание: "Мы отправили вместе с этим сообщением ",
    то верни True, если такого словосочетания нет, то False
    """
    IS_JSON_DESCRIPTION: str = """
    Верни json в таком виде: 
    {
    'Имя ребёнка': *здесь имя из текста*, 
    'Дата рождения': *здесь дата рождения из текста*,
    'Страна/город': *здесь город из текста*,
    'Подробнее о запросе': *здесь данные из 'Подробнее о запросе' из текста*,
    'Диагноз (если есть)': *здесь данные из 'Диагноз (если есть)' из текста*
    }
    """


class RegistrationAssistantTexts:
    @staticmethod
    def survey_completed():
        return (
            "Спасибо за предоставленную информацию! 🙏 "
        )

    @staticmethod
    def approve_appointment_time(time: str):
        return (
            f"Записали вас на пробный урок на {time} по МСК"
            f"\n\n❗Видео по настройке звука в ZOOM, если будете заходить с телефона: "
            f"https://www.youtube.com/shorts/I12qoPB8-r8"
            f"\n❗Присутствие родителя обязательно."
            f"\n❗Урок будет записываться в целях контроля качества."
            f"\n🕓Не позднее, чем за 15 минут диагност отправит ссылку на урок с личного WhatsApp"
            f"\n\nЕсли в день проведения урока вы не подтвердите присутствие, то за 2 часа "
            f"до начала бронь места будет аннулирована"
        )


class SlotsTexts:
    @staticmethod
    async def slot_validation_text():
        _, slots = await SlotsCRUD.read_slots()
        return (
            f"Тебе нужно вернуть ID слота из списка в зависимости от даты, которую ты получаешь"
            f"\n\nВот список слотов:\n{slots}"
        )


class TaskTexts:
    NEED_MANAGER_TEXT: str = "Требуется менеджер для обработки Лида. Запиши на пробное занятие."
    TIME_SELECTED_TEXT: str = "Клиент выбрал время для записи на пу. Забронируй время для диагностики."


class SchedulerTexts:
    SURVEY_30MIN_DELAY: str = (
        "У меня нет задачи замучить Вас своим вниманием 😃 Но Вы оставили заявку и я не могу игнорировать ее."
        "\n\nПодскажите, вы еще заинтересованы в бесплатной диагностике?"
    )
    SURVEY_PASS_TO_MANAGER: str = (
        "Передала данные другому менеджеру, который сможем вам помочь.\n\nПожалуйста, ожидайте ответа 🙏"
    )
    SLOTS_30MIN_DELAY: str = (
        "Ждем вашего ответа для записи на БЕСПЛАТНУЮ диагностику 🤗\nПоторопитесь, чтобы не упустить возможность!"
        "\n🎁 Вам гарантирован БОНУС после записи на диагностику"
        "\nВ какое время хотите посетить занятие? Обязательно подберем для вас удобное🙏"
    )
