import decouple


class SurveyInitialCheckTexts:
    BABY_AGE_TEXT: str = """Тебе нужно привести дату рождения в такой вид: %Y-%m-%d"""
    SEGMENT_TEXT: str = """Возвращаешь только сегмент в виде буквы A, B или С в зависимости от города. A - это все крупные 
    города России с населением более 250 тыс.человек, а также города-миллионники из всех развитых стран. 
    B - это небольшие города России с населением от 100 до 250 тыс. человек, а также столицы стран СНГ, например, 
    Минск или Астана. C - это деревни, сёла, очень маленькие города или любые города из экономически бедных стран."""
    SEGMENT_STATEMENT_TEXT: str = 'Text must contains one of these characters: A, B or C'
    FOR_ONLINE_TEXT: str = """Возвращаешь исключительно True или False. False нужно вернуть в случае, если в разделе 
    Подробнее о запросе или Диагноз есть такие болезни: 
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