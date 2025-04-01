import redis
import json

# клиент для отправки сообщений на сервер отправителя сообщений в тг
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
pubsub = redis_client.pubsub()


def send_tg_message_private(json_user_access_to_this_message: json) -> None:
    try:
        return redis_client.publish('send_tg_private', json_user_access_to_this_message)
    except Exception as e:
        print(f'Ошибка в send_tg_message_private: {e}')
        pass


def presend_filters(type_msg: str, text: str) -> None:
    """ Ищет сотрудников кому положены такие сообщения и шлет сервису json """
    # хочу потом заменить перебор по не созданной модели типа сообщения, чтобы можно было crud модели по отправке сообщений
    from user.models import MsUser
    workers = MsUser.objects.all()
    if type_msg == 'create_application':
        workers = workers.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'delete_application':
        workers = workers.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'daily':
        workers = workers.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'apply_application':
        workers = workers.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    elif type_msg == 'manage_control':
        workers = workers.filter(
            permission__in=('admin', 'technical'))
    elif type_msg == 'departure':
        workers = workers.filter(
            permission__in=('service', 'admin', 'monitoring', 'control', 'all', 'technical'))
    else:
        workers = workers.filter(permission__in=('admin',))

    pre_send_info = {'user_access_to_this_message': [], 'text': text}
    for worker in workers:
        pre_send_info['user_access_to_this_message'].append(
            {
                'chat_id': worker.telegram_id,
                'first_name': worker.first_name,
                'last_name': worker.last_name,
                'status': None

            }
        )

    json_user_access_to_this_message = json.dumps(pre_send_info, ensure_ascii=False)
    send_tg_message_private(json_user_access_to_this_message)
