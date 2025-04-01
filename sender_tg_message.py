import os
import asyncio
from dotenv import load_dotenv
import redis.asyncio as aioredis  # Асинхронный клиент Redis
import aiohttp
import json

"""Отправка """
# Загрузка токена
load_dotenv('Config/.env')
TOKEN = os.getenv('TOKEN')
URL = f'https://api.telegram.org/bot{TOKEN}/'

# Создаем асинхронный Redis-клиент
redis_client = aioredis.StrictRedis(host='localhost', port=6379, db=0)


async def send_message_process(chat_id: str, text: str) -> dict:
    """
    Асинхронная функция для отправки сообщения в Telegram.
    Возвращает статус отправки в тг
    """

    async with aiohttp.ClientSession() as session:
        print('В отправке', text)
        params = {'chat_id': chat_id, 'text': text}
        async with session.post(URL + 'sendMessage', data=params) as response:
            print({chat_id: response.status})
            return {chat_id: response.status}


async def final_msg_report(pre_send_info):
    result_msg = f'{pre_send_info['text'][:10] + "..."}\n'
    status_icon = {200: '🟢', 400: '🔴', 500: ' ⚫️', 0: '🔺'}
    for telegram_person in pre_send_info['user_access_to_this_message']:
        icon = status_icon[telegram_person["status"]] if telegram_person["status"] in status_icon.keys() else telegram_person["status"]
        result_msg += f'{telegram_person["first_name"]} {telegram_person["last_name"]} : {icon}\n'
    await send_message_process(chat_id='319999899', text=result_msg)


message_queue = asyncio.Queue()


async def producer(pubsub):
    """
    Чтение сообщений из Redis и добавление их в очередь.
    """
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        if message:
            print(f'Получен запрос на отправку сообщения: {message["data"]}')
            try:
                data = json.loads(message['data'])
                print(1, data)
                await message_queue.put(data)  # Добавляем задачу в очередь
            except Exception as e:
                print(f"Ошибка добавления в очередь: {e}")
        await asyncio.sleep(0.1)


async def consumer():
    """
    Обработка задач из очереди.
    """
    while True:
        pre_send_info = await message_queue.get()  # Получаем список сообщений

        # Хранение статусов отправки
        for index, telegram_person in enumerate(pre_send_info['user_access_to_this_message']):
            try:
                if not telegram_person["chat_id"]:
                    status = 0
                else:
                    status_dict = await send_message_process(chat_id=telegram_person["chat_id"],
                                                             text=pre_send_info['text'])
                    status = status_dict[telegram_person["chat_id"]]
            except Exception as e:
                print(f"Ошибка отправки сообщения: {e}")
                status = 500  # Ошибка сервера
            finally:
                telegram_person["status"] = status

        message_queue.task_done()

        # Отправляем отчет о статусах всех отправленных сообщений

        await final_msg_report(pre_send_info)


async def main():
    """Запуск сервиса по асинхронной отправке сообщений"""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe('send_tg_private')
    print('Сервис по отправке сообщений начинает включение ')

    # Запускаем производителей и потребителей
    producers = asyncio.create_task(producer(pubsub))
    consumers = [asyncio.create_task(consumer()) for _ in range(7)]  # 4 параллельных задач

    await producers
    await asyncio.gather(*consumers)


if __name__ == "__main__":
    asyncio.run(main())
