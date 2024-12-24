import asyncio
import os

import aiohttp
from dotenv import load_dotenv
from user.models import MsUser

load_dotenv('core_mechanic/Data/Config/.env')
TOKEN = os.getenv('TOKEN')
URL = f'https://api.telegram.org/bot{TOKEN}/'


async def tg_notification(chat_id: int, text: str):
    async with aiohttp.ClientSession() as session:
        params = {'chat_id': chat_id, 'text': text}
        async with session.post(URL + 'sendMessage', data=params) as response:
            return response.status


def send_tg_notification(type_msg: str, text: str) -> dict:
    if type_msg == 'create_application':
        workers = MsUser.objects.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'delete_application':
        workers = MsUser.objects.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'daily':
        workers = MsUser.objects.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'apply_application':
        workers = MsUser.objects.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'server_checker':
        workers = MsUser.objects.filter(
            permission__in=('admin', 'technical'))
    elif type_msg == 'departure':
        workers = MsUser.objects.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    else:
        workers = MsUser.objects.filter(
            permission__in=('admin',))

    response_statuses = {}
    for worker in workers:
        response_statuses[worker] = asyncio.run(tg_notification(chat_id=worker.telegram_id, text=text))
    return response_statuses
