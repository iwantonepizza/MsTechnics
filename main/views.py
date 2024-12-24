from django.shortcuts import render

from core_mechanic.get_time import get_time_setting_tz


def index(request):
    time = get_time_setting_tz
    context = {'title': 'Главная', 'time': time}
    return render(request, 'base.html', context)


def lk(request):
    context = {'title': 'Инфо',
               'is_bubba': 'True'}
    return render(request, 'user/lk.html', context)


def sys_check(request):
    return render(request, 'request_page.html')
