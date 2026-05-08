from apps.core.users.models import MsUser


def create_user(username, email, password):
    try:
        MsUser.objects.create_user(
            username=username,
            email=email,
            password=password
        )
    except Exception as e:
        return e
    return MsUser.objects.get(username=username)


