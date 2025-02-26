from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator, RegexValidator
from django.db import models
from django.db.models import F, Q

from users.config import (LENGTH_TEXT, MAX_LENGTH_EMAIL, MAX_LENGTH_FIRST_NAME,
                          MAX_LENGTH_LAST_NAME, MAX_LENGTH_USERNAME,
                          REGEX_FIELD_USERNAME)


class CustomUser(AbstractUser):
    """Модель переопределенного пользователя."""

    USERNAME_FIELD = 'email'
    USER_ID_FIELD = 'username'
    REQUIRED_FIELDS = (
        'username',
        'first_name',
        'last_name',
        'password'
    )

    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        help_text=(
            'Почта должна быть уникальной. '
            'Поле обязательное. '
            f'Максимум {MAX_LENGTH_EMAIL} символов.'
        ),
        max_length=MAX_LENGTH_EMAIL,
        validators=(EmailValidator(),),
        unique=True,
        blank=False,
        error_messages={
            'unique': 'Такой email уже занят.',
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    username = models.CharField(
        verbose_name='Уникальное имя пользователя',
        help_text=(
            'Имя пользователя должно быть уникальным. '
            'Поле обязательное. '
            f'Максимум {MAX_LENGTH_USERNAME} символов.'
        ),
        max_length=MAX_LENGTH_USERNAME,
        validators=[RegexValidator(
            regex=REGEX_FIELD_USERNAME,
            message=(
                'Имя пользователя содержит недопустимый символ. '
                'Только буквы, цифры и @/./+/-/_.'
            )
        )],
        unique=True,
        blank=False,
        error_messages={
            'unique': 'Пользователь с таким username уже существует.',
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    first_name = models.CharField(
        verbose_name='Имя',
        help_text=(
            'Введите своё имя. Поле обязательное. '
            f'Максимум {MAX_LENGTH_FIRST_NAME} символов.'
        ),
        max_length=MAX_LENGTH_FIRST_NAME,
        blank=False,
        error_messages={
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        help_text=(
            'Введите свою фамилию. Поле обязательное. '
            f'Максимум {MAX_LENGTH_LAST_NAME} символов.'
        ),
        max_length=MAX_LENGTH_LAST_NAME,
        blank=False,
        error_messages={
            'blank': 'Это поле обязательно для заполнения.',
        }
    )
    is_subscribed = models.BooleanField(
        verbose_name='Подписаться на автора',
        blank=True,
        default=False,
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        help_text=(
            'Загрузите фото для своего профиля. '
        ),
        upload_to='users/images/',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self) -> str:
        return f"""{self.username[:LENGTH_TEXT]}: {self.email[:LENGTH_TEXT]}"""


class Subscription(models.Model):
    """Модель подписок пользователей."""

    user = models.ForeignKey(
        to=CustomUser,
        verbose_name='Подписчик',
        on_delete=models.CASCADE,
        related_name='follower',
    )
    following = models.ForeignKey(
        to=CustomUser,
        verbose_name='На кого подписан',
        on_delete=models.CASCADE,
        related_name='following',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ('user__username',)
        constraints = [
            models.CheckConstraint(
                check=~Q(user=F('following')),
                name='%(app_label)s_%(class)s_prevent_self_follow'
            ),
            models.UniqueConstraint(
                fields=('user', 'following',),
                name='unique_user_following'
            )
        ]

    def __str__(self) -> str:
        return f'{self.user} подписан на {self.following}'
