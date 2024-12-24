from django.shortcuts import render
from django.contrib import auth, messages
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from user.forms import UserLoginForm
from django.contrib.auth.decorators import login_required


# Create your views here.
def login(request):
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            username = request.POST['username']
            password = request.POST['password']
            user = auth.authenticate(username=username, password=password)

            # session_key = request.session.session_key

            if user:
                auth.login(request, user)
                messages.success(request, f"{username}, Вы вошли в аккаунт")

                redirect_page = request.POST.get('next', None)
                if redirect_page and redirect_page != reverse('user:logout'):
                    return HttpResponseRedirect(request.POST.get('next'))

                # if session_key:
                # delete old authorized user carts
                # forgot_carts = Cart.objects.filter(user=user)
                # if forgot_carts.exists():
                #  forgot_carts.delete()
                # add new authorized user carts from anonimous session
                # Cart.objects.filter(session_key=session_key).update(user=user)

                return HttpResponseRedirect(reverse('main_menu:index'))
        else:
            messages.error(request, f"Неправильный логин или пароль")
    else:
        form = UserLoginForm()

    context = {
        'title': 'Home - Авторизация',
        'form': form
    }
    return render(request, 'user/login.html', context)


def registration(request):
    context = {'title': 'Меню сервис'}
    return render(request, 'user/registration.html', context)


@login_required
def lk(request):
    context = {'title': 'Меню сервис'}
    return render(request, 'user/lk.html', context)


def logout(request):
    messages.success(request, f"{request.user.username}, Вы вышли из аккаунта")
    auth.logout(request)
    return HttpResponseRedirect(reverse('user:login'))
