from django.contrib import admin
from recipes.config import LIST_ON_PAGE

from .models import CustomUser

admin.site.empty_value_display = '-пусто-'


@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    '''Админ-понель для модели Пользователя.'''

    list_display = (
        'username',
        'email',
        'first_name',
        'last_name'
    )
    list_editable = (
        'email',
    )
    search_fields = (
        'username',
        'email'
    )
    list_display_links = ('username',)
    ordering = ('username',)
    list_per_page = LIST_ON_PAGE
