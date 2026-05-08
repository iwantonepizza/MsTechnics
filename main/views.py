from django.shortcuts import render

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from zip.models import Display


def index(request):
    """Лк пока что в разработке, возможно вырезать"""
    context = {'title': 'Главная'}
    return render(request, 'html/index.html', context)


@login_required
def lk(request):
    """Лк пока что в разработке, возможно вырезать"""
    context = {'title': 'Личный кабинет'}
    return render(request, 'user/lk.html', context)


def sys_check(request):
    """Страница для проверки доступности сайта через сервис"""
    return render(request, 'request_page.html')


@login_required
def get_display_contacts(request, display_id):
    """Получение контакт листа через ajax"""
    display = get_object_or_404(Display, id=display_id)
    contacts = display.contacts.all()

    return render(request, 'modals/contact_list.html', {'contacts': contacts, 'display': display})
