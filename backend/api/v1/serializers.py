from django.forms import ValidationError
from rest_framework import serializers
from rest_framework.response import Response
from recipes.models import (
    Tag, Ingredient, Recipe, RecipeIngredient, ShortLinkRecipe,
    ShoppingList, Follow, Favorite
)
from users.models import CustomUser
from django.contrib.auth import authenticate
from .fields import Base64ImageFieldAvatar


class SignUpSerializer(serializers.ModelSerializer):
    '''Сериализатор для регистрации нового пользователя.'''

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'password', 'is_subscribed',
                  'avatar'
                  )
        extra_kwargs = {'password': {'write_only': True,
                                     'required': True,
                                     }
                        }

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Follow.objects.filter(follower=user, author=obj).exists()
        return False

    def validate(self, data):
        password = data.get('password')
        email = data.get('email')
        if not email:
            raise serializers.ValidationError(
                'email обязателен для заполнения!'
            )
        if not password:
            raise serializers.ValidationError(
                'Пароль обязателен для заполнения!'
            )
        if len(password) < 8:
            raise serializers.ValidationError(
                'Пароль должен иметь не менее 8 символов!'
            )
        return data


class PasswordSerializer(serializers.Serializer):
    '''Сериализатор для обновления пароля.'''

    new_password = serializers.CharField(write_only=True)
    current_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Текущий пароль неверный.')
        return value


class TokenSerializer(serializers.ModelSerializer):
    '''Сериализатор для регистрации токена.'''

    class Meta:
        model = CustomUser
        fields = ('password', 'email')

    def validate(self, data):
        password = data.get('password')
        email = data.get('email')
        user = authenticate(email=email, password=password)
        if not email:
            raise serializers.ValidationError(
                'email не может быть пустым.'
            )
        if not password:
            raise serializers.ValidationError(
                'Пароль не может быть пустым.'
            )
        if not user:
            raise serializers.ValidationError(
                'Пользователь не найден.'
            )

        return data


class ProfileUserSerializer(serializers.ModelSerializer):
    '''Сериализатор для профиля пользователя.'''

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')
        extra_kwargs = {'is_subscribed': {'required': True},
                        'avatar': {'required': True},
                        }

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return user.following.filter(author=obj).exists()
        return False

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None


class UpdateAvatarSerializer(serializers.ModelSerializer):
    '''Сериализатор для добавления аватара.'''

    avatar = Base64ImageFieldAvatar(required=True,)

    class Meta:
        model = CustomUser
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    '''Сериализатор тега рецепта.'''

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    '''Сериализатор для ингредиентов.'''

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    '''Сериализатор для ингредиентов в рецепте.'''

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    '''Сериализатор для рецептов.'''

    author = ProfileUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageFieldAvatar(required=True)
    cooking_time = serializers.IntegerField(required=True, min_value=1)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipeingredient_set', read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('author', 'is_favorited', 'is_in_shopping_cart')

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Favorite.objects.filter(author=user, recipe=obj).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return ShoppingList.objects.filter(user=user, recipe=obj).exists()
        return False

    def validate(self, data):
        name = data.get('name')
        author = self.context['request'].user
        if Recipe.objects.filter(name=name, author=author).exists():
            raise ValidationError('Рецепт с таким именем уже существует.')
        if data['cooking_time'] < 1:
            raise serializers.ValidationError(
                'Время приготовления должно быть больше минуты.')
        return data

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Список ингредиентов не может быть пустым.')
        ingredient_ids = [ingredient.get('id') for ingredient in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.')
        for ingredient in value:
            if 'id' not in ingredient or 'amount' not in ingredient:
                raise serializers.ValidationError(
                    "Каждый ингредиент должен содержать 'id' и 'amount'.")
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть больше нуля.')
        return value

    def create_recipe_ingredient(self, ingredients, recipe):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                ingredient_id=ingredient['id'],
                recipe=recipe,
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ])

    def create(self, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.create_recipe_ingredient(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        instance.name = validated_data.get('name', instance.name)
        instance.image = validated_data.get('image', instance.image)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time)

        if ingredients_data is not None:
            instance.recipeingredient_set.all().delete()
            RecipeIngredient.objects.bulk_create([
                RecipeIngredient(
                    recipe=instance,
                    ingredient_id=ingredient['id'],
                    amount=ingredient['amount']
                )
                for ingredient in ingredients_data
            ])

        if tags_data is not None:
            instance.tags.set(tags_data)

        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(instance.tags, many=True).data
        representation['ingredients'] = RecipeIngredientSerializer(
            instance.recipeingredient_set.all(), many=True
        ).data
        return representation


class ShortLinkRecipeSerializer(serializers.ModelSerializer):
    '''Сериализатор для короткой ссылки.'''

    class Meta:
        model = ShortLinkRecipe
        fields = ('short_link',)

    def to_representation(self, instance):
        rename = super().to_representation(instance)
        rename['short-link'] = rename.pop('short_link')
        return rename


class ShoppingListSerializer(serializers.ModelSerializer):
    '''Сериализатор для списка покупок.'''

    image = Base64ImageFieldAvatar(required=True)
    cooking_time = serializers.IntegerField(required=True, min_value=1)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteSerializer(serializers.ModelSerializer):
    '''Сериализатор для избранного.'''

    image = Base64ImageFieldAvatar(required=True)
    cooking_time = serializers.IntegerField(required=True, min_value=1)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowRecipeSerializer(serializers.ModelSerializer):
    '''Сериализатор для подписок на рецепты.'''

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(serializers.ModelSerializer):
    '''Сериализатор для подписок.'''

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    recipes = FollowRecipeSerializer(many=True, read_only=True, source='recipe_set')
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar'
                  )

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Follow.objects.filter(follower=user, author=obj).exists()
        return False

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
