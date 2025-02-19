from django.contrib import admin
from recipes.models import (FavouriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, RecipeTag, ShoppingList, Tag)

admin.site.site_header = 'Администрирование Foodgram'
admin.site.empty_value_display = '-пусто-'


class BaseFavoriteShopping(admin.ModelAdmin):
    """Базовый класс для Избранного/Списка покупок."""

    list_display = (
        'id',
        'user',
        'recipe',
    )

    list_filter = ('user__username', 'recipe')
    search_fields = ('user__username', 'recipe')


class BaseRecipeIngredientTagInline(admin.StackedInline):
    """Базовый класс для строчного представления."""

    extra = 0
    min_num = 1


class RecipeIngredientInline(BaseRecipeIngredientTagInline):
    """Строчное представление Ингредиента в Рецепте."""

    model = RecipeIngredient


class RecipeTagInline(BaseRecipeIngredientTagInline):
    """Строчное представление Тега в Рецепте."""

    model = RecipeTag


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Админка для рецептов"""

    list_display = (
        'name',
        'get_username',
        'text',
        'image',
        'cooking_time',
        'get_ingredients',
        'get_tags',
        'published_date',
        'added_to_favorite',
    )
    search_fields = (
        'author__username',
        'name'
    )
    list_filter = ('name', 'tags',)
    filter_horizontal = ('tags',)
    inlines = [RecipeIngredientInline, RecipeTagInline]

    @admin.display(
        description='Автор,'
    )
    def get_username(self, object):
        """Автор рецепта."""
        return object.author.username

    @admin.display(
        description='Ингридиенты,'
    )
    def get_ingredients(self, object):
        """Список тегов."""
        return '\n'.join(
            obj.ingredient.name for obj in object.recipe_ingredients.all()
        )

    @admin.display(
        description='Теги'
    )
    def get_tags(self, object):
        """Список тегов."""
        return '\n'.join(obj.tag.name for obj in object.recipe_tags.all())

    @admin.display(
        description='Количество добавлений в избранное'
    )
    def added_to_favorite(self, object):
        """Популярность рецепта."""
        return object.favorite_recipes.count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Админка Тегов."""

    list_display = (
        'id',
        'name',
        'slug',
    )
    list_editable = (
        'name',
        'slug',
    )
    search_fields = (
        'name',
        'slug',
    )
    list_filter = (
        'name',
    )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Админка Ингридиента."""

    list_display = (
        'id',
        'name',
        'measurement_unit',
    )

    list_editable = (
        'name',
        'measurement_unit',
    )

    search_fields = ('name',)
    list_filter = ('name',)


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    """Админка Рецепта/Ингридиента."""

    list_display = (
        'recipe',
        'ingredient',
        'amount',
    )

    list_filter = ('recipe', 'ingredient')
    search_fields = ('recipe__name', 'ingredient__name')
    list_display_links = ('recipe', 'ingredient')


@admin.register(RecipeTag)
class RecipeTagAdmin(admin.ModelAdmin):
    """Админка Рецепта/Тега."""

    list_display = (
        'recipe',
        'tag',
    )

    list_filter = ('recipe', 'tag')
    search_fields = ('recipe__name', 'tag__name')
    list_display_links = ('recipe', 'tag')


@admin.register(FavouriteRecipe)
class FavoriteAdmin(BaseFavoriteShopping):
    """Админка Избранного."""


@admin.register(ShoppingList)
class ShoppingCartAdmin(BaseFavoriteShopping):
    """Админка Списка Покупок."""
