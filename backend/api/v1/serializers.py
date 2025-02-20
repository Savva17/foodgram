from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (FavouriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, RecipeTag, ShoppingList, Tag)
from rest_framework import status
from rest_framework.serializers import (CharField, IntegerField,
                                        ModelSerializer,
                                        PrimaryKeyRelatedField,
                                        SerializerMethodField, SlugField,
                                        ValidationError)
from rest_framework.validators import UniqueTogetherValidator
from users.config import MAX_LENGTH_PASSWORD, MIN_LENGTH_PASSWORD
from users.models import CustomUser, Subscription

from .fields import Base64ImageFieldAvatar


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания пользователя."""

    password = CharField(
        max_length=MAX_LENGTH_PASSWORD,
        min_length=MIN_LENGTH_PASSWORD,
        write_only=True,
        required=True
    )

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )

    def validate_username(self, username: str) -> str:
        """Проверяет, чтобы пользователь не присваивал себе имя "me"."""
        if username == 'me':
            raise ValidationError(
                'Использовать имя "me" запрещено.'
            )
        return username

    def create(self, validated_data: dict) -> CustomUser:
        """Создаёт нового пользователя."""
        user = CustomUser(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
        )
        password = validated_data.pop('password')
        user.set_password(password)
        user.save()
        return user


class CustomUserSerializer(UserSerializer):
    """Сериализатор для работы с пользователем."""

    is_subscribed = SerializerMethodField(
        method_name='get_subscribe_status'
    )
    avatar = Base64ImageFieldAvatar(
        allow_null=True,
        required=False
    )

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )
        read_only_fields = (
            'id',
            'is_subscribed',
        )

    def get_subscribe_status(self, obj: CustomUser) -> bool:
        """Проверяет подписку пользователя."""
        user = self.context.get('request').user
        is_anonym = user is None or user.is_anonymous or user == obj
        if is_anonym:
            return False
        return (
            user.follower.filter(following=obj).exists()
        )


class AvatarSerializer(ModelSerializer):
    """Сериализатор аватарки."""

    avatar = Base64ImageFieldAvatar()

    class Meta:
        model = CustomUser
        fields = (
            'avatar',
        )


class ShowSubscriptionSerializer(CustomUserSerializer):
    """Сериализатор для отображения подписок пользователя."""

    recipes_count = SerializerMethodField(
        method_name='get_recipes_count'
    )
    recipes = SerializerMethodField(
        method_name='get_recipes'
    )

    class Meta(CustomUserSerializer.Meta):
        model = CustomUser
        fields = CustomUserSerializer.Meta.fields + (
            'recipes_count',
            'recipes',
        )

    def get_recipes_count(self, obj) -> int:
        return Recipe.objects.filter(author=obj).count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        limit = request.query_params.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = ShowFavoriteRecipeSerializer(
            recipes,
            many=True,
            read_only=True,
            context={'request': request}
        )
        return serializer.data


class CreateSubscriptionSerializer(ModelSerializer):
    """Сериализатор для создания подписок пользователя."""

    class Meta:
        model = Subscription
        fields = (
            'user',
            'following',
        )
        validators = [
            UniqueTogetherValidator(
                fields=('user', 'following'),
                queryset=model.objects.all(),
                message='Подписка на автора была оформлена ранее!',
            )
        ]

    def validate_following(self, data):

        if self.context.get('request').user == data:
            raise ValidationError(
                detail='Невозможно оформить подписку на самого себя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        return data

    def to_representation(self, instance):
        request = self.context.get('request')
        return ShowSubscriptionSerializer(
            instance.following, context={'request': request}
        ).data


class GetRecipeTagSerializer(ModelSerializer):
    """Сериализатор получения связи рецепта и тега."""

    id = IntegerField(source='tag.id')
    name = CharField(source='tag.name')
    slug = SlugField(source='tag.slug')

    class Meta:
        model = RecipeTag
        fields = (
            'id',
            'name',
            'slug'
        )


class TagSerializer(ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'slug',
        )


class GetRecipeIngredientsSerializer(ModelSerializer):
    """Сериализатор получения связи рецепта и ингредиента."""

    id = IntegerField(source='ingredient.id')
    name = CharField(source='ingredient.name')
    measurement_unit = CharField(source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount'
        )


class IngredientSerializer(ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit',
        )


class CreateRecipeIngredientSerializer(ModelSerializer):
    """Сериализатор создания связи рецепта и ингредиента."""

    id = PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'amount'
        )

    def validate_amount(self, value):
        if not value:
            ValidationError('Поле amount не может быть пустым.')
        return value


class ShowFavoriteRecipeSerializer(ModelSerializer):
    """Сериализатор для отображения избранных рецептов."""

    image = Base64ImageFieldAvatar()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class GetRecipeSerializer(ModelSerializer):
    """Сериализатор получения полной информации Рецепта."""

    tags = GetRecipeTagSerializer(
        many=True,
        source='recipe_tags'
    )
    author = CustomUserSerializer(
        read_only=True
    )
    ingredients = GetRecipeIngredientsSerializer(
        many=True,
        source='recipes_ingredients'
    )
    is_favorited = SerializerMethodField(
        method_name='get_is_favorited'
    )
    is_in_shopping_cart = SerializerMethodField(
        method_name='get_is_in_shopping_cart'
    )
    image = Base64ImageFieldAvatar()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def check_is_favorited_or_in_shopping_list(self, obj, related_field):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and getattr(request.user, related_field).filter(
                recipe=obj).exists()
        )

    def get_is_favorited(self, obj):
        return self.check_is_favorited_or_in_shopping_list(
            obj, 'favourite'
        )

    def get_is_in_shopping_cart(self, obj):
        return self.check_is_favorited_or_in_shopping_list(
            obj, 'shopping_list'
        )


class CreateRecipeSerializer(ModelSerializer):
    """Сериализатор создания Рецепта."""

    tags = PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    ingredients = CreateRecipeIngredientSerializer(
        many=True,
        source='recipes_ingredients'
    )
    image = Base64ImageFieldAvatar()

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    def validate(self, data):
        tags = data.get('tags')
        ingredients = data.get('recipes_ingredients')
        if not tags:
            raise ValidationError(
                'Отсутствует обязательное поле tags.'
            )
        if not ingredients:
            raise ValidationError(
                'Отсутствует обязательное поле ingredients.'
            )

        ingredients_length = len(ingredients)
        if not ingredients_length:
            raise ValidationError('Не может быть пустым.')
        ingredients_id = [
            ingredient['ingredient'].id for ingredient in ingredients
        ]
        if len(set(ingredients_id)) != ingredients_length:
            raise ValidationError(
                'Данные должны быть уникальными.'
            )
        tags_length = len(tags)
        if not tags_length:
            raise ValidationError('Не может быть пустым.')
        if len(set(tags)) != tags_length:
            raise ValidationError(
                'Данные должны быть уникальными.'
            )

        return data

    def validate_image(self, value):
        if value:
            return value
        raise ValidationError(
            'Не может быть пустым.'
        )

    def add_ingredients(self, model, recipe, ingredients):
        model.objects.bulk_create(
            (
                model(
                    recipe=recipe,
                    ingredient=ingredient['ingredient'],
                    amount=ingredient['amount']
                )
                for ingredient in ingredients
            )
        )

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipes_ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self.add_ingredients(RecipeIngredient, recipe, ingredients)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipes_ingredients')
        recipes_ingredients = RecipeIngredient.objects.filter(recipe=instance)
        recipe_tags = RecipeTag.objects.filter(recipe=instance)
        recipe_tags.delete()
        recipes_ingredients.delete()
        instance.tags.set(tags)
        self.add_ingredients(RecipeIngredient, instance, ingredients)

        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return GetRecipeSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data


class FavouriteRecipeSerializer(ModelSerializer):
    """Сериализатор добавления рецептов в избранное."""

    class Meta:
        model = FavouriteRecipe
        fields = (
            'user',
            'recipe'
        )

    def validate(self, data):
        is_favorite = FavouriteRecipe.objects.filter(**data).exists()
        if is_favorite:
            raise ValidationError(
                f'Рецепт \'{data["recipe"]}\''
                'уже добавлен в избранное.'
            )
        return data

    def to_representation(self, instance):
        return ShowFavoriteRecipeSerializer(
            instance.recipe
        ).data


class ShoppingCartRecipeSerializer(ModelSerializer):
    """Сериализатор добавления рецептов в список покупок."""

    class Meta:
        model = ShoppingList
        fields = (
            'user',
            'recipe'
        )

    def validate(self, data):
        is_in_cart = ShoppingList.objects.filter(**data).exists()
        if is_in_cart:
            raise ValidationError(
                f'Рецепт \'{data["recipe"]}\''
                'уже добавлен в список покупок.'
            )
        return data

    def to_representation(self, instance):
        return ShowFavoriteRecipeSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data
