from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from recipes.config import (MAX_LENGTH_EMAIL, MAX_LENGTH_USERNAME,
                            REGEX_FIELD_USERNAME, MAX_LENGTH_FIRST_NAME,
                            MAX_LENGTH_LAST_NAME
                            )


class CustomUser(AbstractUser):
    """Модель кастомного пользователя."""

    email = models.EmailField(
        verbose_name='Адрес электронной почты',
        help_text=(
            'Почта должна быть уникальной.'
        ),
        unique=True,
        max_length=MAX_LENGTH_EMAIL
    )
    username = models.CharField(
        verbose_name='Уникальный юзернейм',
        max_length=MAX_LENGTH_USERNAME,
        help_text=(
            'Юзернейм должно быть уникальным.'
        ),
        validators=[RegexValidator(
            regex=REGEX_FIELD_USERNAME,
            message=(
                'Юзернейм содержит недопустимый символ. '
                'Только буквы, цифры и @/./+/-/_.'
            )
        )],
        unique=True
    )
    first_name = models.CharField(
        verbose_name='Имя',
        help_text=(
            'Введите своё имя. Поле обязательное.'
        ),
        max_length=MAX_LENGTH_FIRST_NAME
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        help_text=(
            'Введите свою фамилию. Поле обязательное.'
        ),
        max_length=MAX_LENGTH_LAST_NAME,
    )
    avatar = models.ImageField(
        verbose_name='Аватар',
        upload_to='users/',
        blank=True,
        help_text='Загрузите аватар пользователя.'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'last_name', 'first_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username', 'last_name')

    def __str__(self):
        return f'{self.username} ({self.email}).'
