import structlog
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from user.forms import UserLoginForm

logger = structlog.get_logger(__name__)


def login(request):
    if request.method == "POST":
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            username = request.POST["username"]
            password = request.POST["password"]
            user = auth.authenticate(username=username, password=password)
            if user:
                auth.login(request, user)
                messages.success(request, f"{username}, Вы вошли в аккаунт")
                logger.info("user_login", username=username)
                redirect_page = request.POST.get("next", None)
                if redirect_page and redirect_page != reverse("user:logout"):
                    return HttpResponseRedirect(redirect_page)
                return HttpResponseRedirect(reverse("main_menu:index"))
        else:
            messages.error(request, "Неправильный логин или пароль")
    else:
        form = UserLoginForm()
    return render(request, "user/login.html", {"title": "Авторизация", "form": form})


# SEC-007: registration view УДАЛЕНА — создавала захардкоженного юзера при любом GET


@login_required
def lk(request):
    return render(request, "user/lk.html", {"title": "Личный кабинет"})


def logout(request):
    username = request.user.username
    messages.success(request, f"{username}, Вы вышли из аккаунта")
    logger.info("user_logout", username=username)
    auth.logout(request)
    return HttpResponseRedirect(reverse("user:login"))
