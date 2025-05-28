from django.contrib import admin


from user.models import MsUser


# admin.site.register(User)

@admin.register(MsUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "first_name", "last_name", "email", ]
    search_fields = ["username", "first_name", "last_name", "email", ]

