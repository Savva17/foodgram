import csv
from django.http import HttpResponse
from recipes.models import (
    Favorite, Tag, Recipe, Ingredient, ShoppingList, ShortLinkRecipe, Follow
)
from users.models import CustomUser
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import (
    IsAuthenticated, IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from .pagination import CustomPagination
from .permissions import IsAuthorOrReadOnly, IsAuthor
from .serializers import (
    FollowSerializer, ShoppingListSerializer, SignUpSerializer,
    ProfileUserSerializer, TokenSerializer,
    UpdateAvatarSerializer, PasswordSerializer, TagSerializer,
    RecipeSerializer, IngredientSerializer,
    ShortLinkRecipeSerializer, FavoriteSerializer
)
from django.db.models import Exists, OuterRef


class UserViewSet(viewsets.ModelViewSet):
    '''Вьюсет для создания обьектов класса User.'''

    queryset = CustomUser.objects.all()
    serializer_class = SignUpSerializer
    permission_classes = [AllowAny]
    pagination_class = CustomPagination

    @action(detail=False, methods=['post'], url_path='set_password',
            permission_classes=[IsAuthenticated,]
            )
    def set_password(self, request):
        user = request.user
        serializer = PasswordSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST
                        )

    @action(detail=False, url_path='me', permission_classes=[AllowAny])
    def profile_user(self, request):
        if request.user.is_anonymous:
            return Response({'detail': 'Пользователь не авторизован.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        serializer = ProfileUserSerializer(
            request.user, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False, methods=['PUT', 'DELETE'], url_path='me/avatar',
        permission_classes=[IsAuthenticated]
    )
    def avatar_user(self, request):
        user = request.user
        if request.method == 'PUT':
            serializer = UpdateAvatarSerializer(user, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'DELETE':
            user.avatar.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=['post', 'delete'], url_path='subscribe',
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        user = request.user
        author = get_object_or_404(CustomUser, id=pk)

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'detail': 'Нельзя подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Follow.objects.filter(follower=user, author=author).exists():
                return Response(
                    {'detail': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.create(follower=user, author=author)

            serializer = FollowSerializer(
                author,
                context={'request': request, 'is_subscribed': False}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            follow = Follow.objects.filter(follower=user, author=author)
            if not follow.exists():
                return Response(
                    {'detail': 'Вы не подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            follow.delete()
            return Response(
                {'detail': 'Вы отписались от пользователя.'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(detail=False, methods=['get'], url_path='subscriptions',
            permission_classes=(IsAuthenticated,)
            )
    def subscriptions(self, request):
        user = request.user
        subscriptions = CustomUser.objects.filter(
            author_follower__follower=user
        )
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = FollowSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = FollowSerializer(
            subscriptions, many=True, context={'request': request}
        )
        return Response(serializer.data)


class TokenViewSet(viewsets.ModelViewSet):

    queryset = CustomUser.objects.all()
    serializer_class = TokenSerializer


class TagViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny, )
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    '''ViewSet для работы с рецептами.'''

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['author']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAuthorOrReadOnly()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        author_id = self.request.query_params.get('author')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart')
        is_favorited = self.request.query_params.get('is_favorited')
        if is_favorited is not None and user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(author=user, recipe=OuterRef('pk'))
                )
            )
            if is_favorited == '1':
                queryset = queryset.filter(is_favorited=True)
            elif is_favorited == '0':
                queryset = queryset.filter(is_favorited=False)
        if is_in_shopping_cart and self.request.user.is_authenticated:
            if is_in_shopping_cart == '1':
                queryset = queryset.filter(
                    shopping_list__user=self.request.user
                )
            elif is_in_shopping_cart == '0':
                queryset = queryset.exclude(
                    shopping_list__user=self.request.user
                )
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        return queryset

    def destroy(self, request, *args, **kwargs):
        recipe = self.get_object()
        if recipe.author != request.user:
            return Response(
                {'detail': 'Вы не можете удалить чужой рецепт.'},
                status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        self.check_object_permissions(request, instance)

        if 'ingredients' in request.data and not request.data['ingredients']:
            return Response(
                {'ingredients': ['Нужно указать хотя бы один ингредиент.']},
                status=status.HTTP_400_BAD_REQUEST)
        elif 'amount' in request.data and not request.data['amount'] < 1:
            return Response(
                {'amount': ['Нужно указать хотя бы один ингредиент.']},
                status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        recipe = self.get_object()
        self.check_object_permissions(request, recipe)
        if 'ingredients' not in request.data:
            return Response(
                {'ingredients': ['Это поле является обязательным.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        ingredients_data = request.data.get('ingredients', [])
        if 'tags' not in request.data:
            return Response(
                {'tags': ['Это поле является обязательным.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        ingredients_data = request.data.get('ingredients', [])
        if not ingredients_data:
            return Response(
                {'ingredients': ['Нужно указать хотя бы один ингредиент.']},
                status=status.HTTP_400_BAD_REQUEST
            )

        ingredient_ids = [
            ingredient['id'] for ingredient in ingredients_data
            if 'id' in ingredient
        ]
        ingredient_count = Ingredient.objects.filter(id__in=ingredient_ids)
        if not ingredient_count.count() == len(ingredient_ids):
            return Response(
                {'ingredients': ['Указанных ингредиентов не существует.']},
                status=status.HTTP_400_BAD_REQUEST
            )
        if 'tags' in request.data and not request.data['tags']:
            return Response({'tags': ['Нужно указать хотя бы один тег.']},
                            status=status.HTTP_400_BAD_REQUEST)
        tags = request.data.get('tags', [])
        if len(tags) != len(set(tags)):
            return Response({'tags': ['Теги не должны повторяться.']},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(
            recipe, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, url_path='get-link', permission_classes=[AllowAny])
    def get_short_link_recipe(self, request, pk=None):
        try:
            recipe = Recipe.objects.get(id=pk)
        except Recipe.DoesNotExist:
            return Response({'detail': "Рецепт не найден"},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            short_link_recipe = ShortLinkRecipe.objects.get(recipe=recipe)
        except ShortLinkRecipe.DoesNotExist:
            return Response(
                {'detail': "Нет короткой ссылки для этого рецепта"},
                status=status.HTTP_404_NOT_FOUND)

        serializer = ShortLinkRecipeSerializer(short_link_recipe)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True, methods=['post', 'delete'], url_path='favorite',
        permission_classes=[IsAuthenticated]
    )
    def add_delete_recipe_in_favorite(self, request, pk=None):
        user = request.user
        if user.is_anonymous:
            return Response({'error': 'Необходимо войти в систему'},
                            status=status.HTTP_401_UNAUTHORIZED)
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            if Favorite.objects.filter(author=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже есть в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(author=user, recipe=recipe)
            serializer = FavoriteSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            favorite_item = Favorite.objects.filter(
                author=user, recipe=recipe)
            if not favorite_item.exists():
                return Response(
                    {'detail': 'Рецепт не найден в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            favorite_item.delete()
            return Response(
                {'detail': 'Рецепт удален из избранного'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=True, methods=['post', 'delete'], url_path='shopping_cart',
        permission_classes=[IsAuthenticated]
    )
    def add_delete_recipe_for_shopping_list(self, request, pk=None):
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Аутентификация требуется.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            if ShoppingList.objects.filter(
                    user=request.user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже есть в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingList.objects.create(user=request.user, recipe=recipe)

            serializer = ShoppingListSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            shopping_item = ShoppingList.objects.filter(
                user=request.user, recipe=recipe)
            if not shopping_item.exists():
                return Response(
                    {'detail': 'Рецепт не найден в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            shopping_item.delete()
            return Response(
                {'detail': 'Рецепт удален из списка покупок.'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(
        detail=False, methods=['get'], url_path='download_shopping_cart',
        permission_classes=[IsAuthenticated]
    )
    def download_csv(self, request):
        """Метод для скачивания CSV файла."""
        response = HttpResponse(content_type='text/csv')
        response["Content-Disposition"] = (
            'attachment; filename="shopping_list.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(['User', 'Recipe'])
        shopping_list = ShoppingList.objects.filter(user=request.user)
        for item in shopping_list:
            writer.writerow([item.user.username, item.recipe.name])
        return response


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny, )
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('name',)
