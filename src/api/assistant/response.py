import aiohttp

from src.core.config import settings, headers


class AssistantResponse:
    @staticmethod
    async def get_response(user_prompt: str, thread_id=None):
        """
        Здесь мы отправляем запрос ассистенту и получаем от него ответ

        :param user_prompt: Текст вопроса пользователя
        :param thread_id: ID треда пользователя
        :return: Ответ ассистента
        """

        url = settings.ASSISTANT_SUBDOMAIN_URL + "/get_response"
        data = {
                'user_prompt': user_prompt,
                'thread_id': thread_id
            } if thread_id else {
                'user_prompt': user_prompt
            }
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, headers=headers.ASSISTANT_HEADERS, json=data) as response:
                if response.status == 200:
                    response_json = await response.json()
                    response_text = response_json.get('response')
                    thread_id = response_json.get('thread_id')
                    return response_text, thread_id
                else:
                    return f"Возникла ошибка {response.status} c текстом:\n{await response.text()}"
