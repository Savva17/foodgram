import random
import string

from django.db.models.signals import post_save
from django.db import models
from django.core.validators import MinValueValidator
from django.dispatch import receiver

from .config import (MAX_LENGTH_NAME_FIELD, MAX_LENGTH_NAME_INGREDIENTS,
                     MAX_LENGTH_UNIT, MAX_LENGTH_NAME_RECIPE, MIN_COOKING_TIME,
                     MIN_QUANTITY, MAX_LENGTH_SLUG, MAX_LENGTH_SHORT_LINK
                     )
from users.models import CustomUser


class Tag(models.Model):
    '''Модель Тега.'''

    name = models.CharField(
        verbose_name='Название тега',
        max_length=MAX_LENGTH_NAME_FIELD,
        unique=True
    )
    slug = models.SlugField(
        verbose_name='Слаг',
        max_length=MAX_LENGTH_SLUG,
        unique=True
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return f'Тег - {self.name}'


class Ingredient(models.Model):
    '''Модель Ингредиента.'''

    name = models.CharField(
        verbose_name='Название ингредиента',
        max_length=MAX_LENGTH_NAME_INGREDIENTS
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения ингредиента',
        max_length=MAX_LENGTH_UNIT
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f'{self.name}, ({self.measurement_unit})'


class Recipe(models.Model):
    '''Модель рецептов.'''

    name = models.CharField(
        verbose_name='Название рецепта',
        max_length=MAX_LENGTH_NAME_RECIPE,
    )
    author = models.ForeignKey(
        CustomUser,
        verbose_name='Автор',
        help_text=(
            'Автор рецепта'
        ),
        on_delete=models.CASCADE
    )
    image = models.ImageField(
        verbose_name='Фото',
        upload_to='recipes/images/',
    )
    text = models.TextField(
        verbose_name='Описание рецепта'
    )
    cooking_time = models.PositiveIntegerField(
        verbose_name='Время приготовления',
        help_text=(
            'Время приготовления не меньше минуты.'
        ),
        default=MIN_COOKING_TIME,
        validators=[
            MinValueValidator(
                MIN_COOKING_TIME,
                message='Введенная время меньше минуты.'
            ),
        ]
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Названия ингредиента',
        through='RecipeIngredient'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тег'
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'author'),
                name='unique_recipe_author',
            ),
        )

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    '''Вспомогательная модель для ингредиентов и рецептов.'''

    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE
    )
    amount = models.PositiveIntegerField(
        verbose_name='Кол-во ингредиентов',
        help_text=(
            'Кол-во ингредиентов не меньше одного.'
        ),
        default=MIN_QUANTITY,
        validators=[
            MinValueValidator(
                MIN_QUANTITY,
                message='Кол-во ингредиентов меньше одного.'
            ),
        ]
    )

    class Meta:
        verbose_name = 'Ингредиенты рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient',
            ),
        )

    def __str__(self):
        return f'В рецепте {self.recipe}, ингредиенты {self.ingredient}'


class Favorite(models.Model):
    '''Модель Избранного.'''

    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        CustomUser,
        verbose_name='Автор',
        on_delete=models.CASCADE
    )

    class Meta:
        default_related_name = 'favorite'
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'author'),
                name='unique_favorites',
            ),
        )

    def __str__(self):
        return (
            f'Рецепт {self.recipe}, в избранном у пользователя {self.author}.'
        )


class ShoppingList(models.Model):
    '''Модель список покупок.'''

    user = models.ForeignKey(
        CustomUser,
        verbose_name='Пользователь',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE
    )

    class Meta:
        default_related_name = 'shopping_list'
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'user'),
                name='unique_shopping_list',
            ),
        )

    def __str__(self):
        return (
            f'Рецепт {self.recipe}, в списке покупок у {self.user}.'
        )


class Follow(models.Model):
    '''Модель подписки.'''

    author = models.ForeignKey(
        CustomUser,
        verbose_name='Автор',
        related_name='author_follower',
        on_delete=models.CASCADE
    )
    follower = models.ForeignKey(
        CustomUser,
        verbose_name='Подписчик',
        related_name='following',
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('author', 'follower'),
                name='unique_follower',
            ),
        )

    def __str__(self):
        return f'{self.follower} подписан на {self.author}'


class ShortLinkRecipe(models.Model):
    '''Модель для создания короткой ссылки.'''

    recipe = models.OneToOneField(
        Recipe, on_delete=models.CASCADE,
        verbose_name='Рецепт'
        )
    short_link = models.CharField(
        verbose_name='Короткая ссылка рецепта',
        max_length=MAX_LENGTH_SHORT_LINK,
        unique=True
    )

    class Meta:
        verbose_name = 'Короткая ссылка'
        verbose_name_plural = 'Короткие ссылки'

    def __str__(self):
        return f'Короткая сслыка {self.short_link}, для {self.recipe}'

    @receiver(post_save, sender=Recipe)
    def create_short_link(sender, instance, created, **kwargs):
        """Создаем короткую ссылку для рецепта, если он только что создан."""
        if created:
            return ShortLinkRecipe.objects.create(recipe=instance)

    @staticmethod
    def generate_unique_short_link():
        """Генерирует уникальную короткую ссылку."""
        while True:
            short_link = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            if not ShortLinkRecipe.objects.filter(short_link=short_link).exists():
                return short_link

    def save(self, *args, **kwargs):
        if not self.short_link:
            self.short_link = self.generate_unique_short_link()
        super().save(*args, **kwargs)
