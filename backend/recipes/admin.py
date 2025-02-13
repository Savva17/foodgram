from django.contrib import admin
from .models import Tag, Ingredient, Recipe

admin.site.empty_value_display = '-пусто-'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    '''Админ-панель для модели Тега.'''

    list_display = (
        'name',
        'slug'
    )
    list_editable = (
        'slug',
    )
    search_fields = ('name',)
    list_filter = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    '''Админ-панель для модели Ингредиента.'''

    list_display = (
        'name',
        'measurement_unit'
    )
    search_fields = ('name',)
    list_filter = ('name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    '''Админ-панель для модели Ингредиента.'''

    list_display = (
        'name',
        'author',
        'count_favorite'
    )
    search_fields = ('author', 'name')
    list_filter = ('tags',)

    def count_favorite(self, obj):
        '''Общее число добавлений этого рецепта в избранное'''
        return obj.favorite.count()
