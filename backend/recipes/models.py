from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from recipes.config import (INGREDIENT_LENGTH_NAME, LENGTH_LONG_TEXT,
                            LENGTH_SHORT_TEXT, MAX_LENGTH_NAME,
                            MAX_LENGTH_SLUG, MAX_LENGTH_TAG, MAX_LENGTH_URL,
                            MEASUREMENT_UNIT_LENGTH, MIN_AMOUNT_SUM,
                            MIN_COOKING_TIME, REGEX_FIELD_SLUG)

User = get_user_model()


class Ingredient(models.Model):
    """Модель ингредиента."""

    name = models.CharField(
        verbose_name='Название',
        help_text=(
            'Введите название ингредиента. '
            f'Максимум {INGREDIENT_LENGTH_NAME} символов.'
        ),
        max_length=INGREDIENT_LENGTH_NAME,
        blank=False,
        error_messages={
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    measurement_unit = models.CharField(
        verbose_name='Единица величины',
        help_text=(
            'Введите единицу величины ингредиента. '
            f'Максимум {MEASUREMENT_UNIT_LENGTH} символов.'
        ),
        max_length=MEASUREMENT_UNIT_LENGTH,
        blank=False,
        error_messages={
            'blank': 'Это поле обязательно для заполнения.',
        }
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit',),
                name='unique_name_measurement_unit'
            ),
        )

    def __str__(self) -> str:
        return f"""{self.name}, {self.measurement_unit}"""


class Tag(models.Model):
    """Модель тега."""

    name = models.CharField(
        verbose_name='Название тега',
        help_text=(
            'Введите название тега. '
            'Тег должен быть уникальным. '
            f'Максимум {MAX_LENGTH_TAG} символов.'
        ),
        max_length=MAX_LENGTH_TAG,
        unique=True,
        blank=False,
        error_messages={
            'unique': 'Такой тег уже занят.',
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    slug = models.SlugField(
        verbose_name='Идентификатор slug',
        help_text=(
            'Введите идентификатор страницы для URL. '
            'Идентификатор должен быть уникальным. '
            f'Максимум {MAX_LENGTH_SLUG} символов.'
        ),
        max_length=MAX_LENGTH_SLUG,
        validators=(
            RegexValidator(
                regex=REGEX_FIELD_SLUG,
                message=(
                    'Разрешены символы латиницы, цифры, дефис и подчёркивание.'
                ),
            ),
        ),
        unique=True,
        blank=False,
        error_messages={
            'unique': 'Такой slug уже занят.',
            'blank': 'Это поле обязательно для заполнения.',
        }
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ('-id',)
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'slug',),
                name='unique_tag'
            ),
        )

    def __str__(self) -> str:
        return f"""{self.name}: {self.slug}"""


class Recipe(models.Model):
    """Модель рецепта."""

    ingredients = models.ManyToManyField(
        to=Ingredient,
        verbose_name='Ингредиенты',
        help_text=(
            'Введите список ингредиентов. '
            'Это продукты для приготовления блюда по рецепту.'
        ),
        through='RecipeIngredient',
        through_fields=('recipe', 'ingredient',),
        blank=False,
        error_messages={
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    tags = models.ManyToManyField(
        to=Tag,
        through='RecipeTag',
        through_fields=('recipe', 'tag',),
        verbose_name='Теги',
        help_text=(
            'Выберите тег. '
            'Можно установить несколько тегов на один рецепт.'
        )
    )
    image = models.ImageField(
        verbose_name='Картинка',
        help_text='Добавьте изображение рецепта',
        upload_to='recipes/images/',
        blank=False,
        error_messages={
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    name = models.CharField(
        verbose_name='Название',
        help_text=(
            'Введите название рецепта. '
            f'Максимум {MAX_LENGTH_NAME} символов.'
        ),
        max_length=MAX_LENGTH_NAME,
        blank=False,
        error_messages={
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    text = models.TextField(
        verbose_name='Описание',
        help_text='Введите описание рецепта.',
        blank=False,
        error_messages={
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления',
        help_text='Введите время приготовления (в минутах).',
        validators=(
            MinValueValidator(MIN_COOKING_TIME),
        ),
        blank=False,
        error_messages={
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    author = models.ForeignKey(
        to=User,
        verbose_name='Автор рецепта',
        help_text='Выберите автора рецепта.',
        on_delete=models.CASCADE
    )
    published_date = models.DateTimeField(
        verbose_name='Дата и время публикации',
        auto_now_add=True,
        editable=False,
    )
    short_link = models.CharField(
        verbose_name='Короткий URL',
        max_length=MAX_LENGTH_URL,
        blank=True,
    )

    class Meta:
        default_related_name = 'recipes'
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-published_date', 'name',)

    def __str__(self) -> str:
        return (
            f"""
            {self.name[:LENGTH_SHORT_TEXT]}
             - {self.text[:LENGTH_LONG_TEXT]}...
            """
        )


class RecipeTag(models.Model):
    """Модель для связи рецепта и тега."""

    recipe = models.ForeignKey(
        to=Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
    )
    tag = models.ForeignKey(
        to=Tag,
        verbose_name='Тег',
        on_delete=models.CASCADE,
    )

    class Meta:
        default_related_name = 'recipe_tags'
        verbose_name = 'Связь рецепта и тега'
        verbose_name_plural = 'Связи рецептов и тегов'
        ordering = ('recipe',)
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'tag',),
                name='unique_recipe_tag',
            ),
        )

    def __str__(self) -> str:
        return (
            f"""
            Рецепт "{self.recipe}"
             содержит теги: {self.tag}.
            """
        )


class RecipeIngredient(models.Model):
    """Промежуточная модель для связи рецепта и ингридиента"""

    recipe = models.ForeignKey(
        to=Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        to=Ingredient,
        verbose_name='Ингредиент',
        on_delete=models.CASCADE
    )
    amount = models.PositiveIntegerField(
        verbose_name='Количество',
        help_text='Введите количество ингредиента.',
        validators=(
            MinValueValidator(
                MIN_AMOUNT_SUM,
                f'Минимальное количество: {MIN_AMOUNT_SUM}',
            ),
        )
    )

    class Meta:
        default_related_name = 'recipes_ingredients'
        verbose_name = 'Связь рецепта и ингридиента'
        verbose_name_plural = 'Связи рецептов и ингридиентов'
        ordering = ('recipe',)
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient',),
                name='unique_recipe_ingredient',
            ),
        )

    def __str__(self) -> str:
        return (
            f"""
            Рецепт "{self.recipe}"
             содержит ингредиент: {self.ingredient}.
            """
        )


class BaseFavouriteAndShopping(models.Model):
    """Базвоая модель для избранных рецептов и списка покупок."""

    user = models.ForeignKey(
        to=User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        to=Recipe,
        verbose_name='Избранный рецепт',
        on_delete=models.CASCADE
    )

    class Meta:
        abstract = True
        ordering = ('user',)


class FavouriteRecipe(BaseFavouriteAndShopping):
    """Модель для избранных рецептов."""

    class Meta(BaseFavouriteAndShopping.Meta):
        default_related_name = 'favourite'
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favourite_recipe',
            ),
        )

    def __str__(self) -> str:
        return (
            f"""
            Пользователь "{self.user}"
             добавил рецепт: {self.recipe}
             в избранное.
            """
        )


class ShoppingList(BaseFavouriteAndShopping):
    """Модель для хранения списка покупок."""

    class Meta(BaseFavouriteAndShopping.Meta):
        default_related_name = 'shopping_list'
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shopping_list_user',
            ),
        )

    def __str__(self) -> str:
        return (
            f"""
            Пользователь "{self.user}"
             добавил рецепт: {self.recipe}
             в список покупок.
            """
        )
