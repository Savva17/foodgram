import uuid

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserViewSer
from recipes.config import SHORT_LINK_MAX_POSTFIX, URL
from recipes.models import (FavouriteRecipe, Ingredient, Recipe,
                            RecipeIngredient, ShoppingList, Tag)
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from users.models import CustomUser, Subscription

from .filters import IngredientFilterSet, RecipeFilterSet
from .pagination import CustomPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (AvatarSerializer, CreateRecipeSerializer,
                          CreateSubscriptionSerializer,
                          CustomUserCreateSerializer, CustomUserSerializer,
                          FavouriteRecipeSerializer, GetRecipeSerializer,
                          IngredientSerializer, ShoppingCartRecipeSerializer,
                          ShowSubscriptionSerializer, TagSerializer)


class UserViewSet(DjoserViewSer):
    """Вьюсет для создания обьектов класса CustomUser."""

    queryset = CustomUser.objects.all()
    serializer_class = CustomUserCreateSerializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if (
            self.action == 'list'
            or self.action == 'retrieve'
            or self.action == 'me'
        ):
            return CustomUserSerializer
        return super().get_serializer_class()

    @action(
        methods=['get'],
        detail=False,
        permission_classes=[IsAuthenticated,],
        url_path='me',
        url_name='me'
    )
    def me(self, request):
        """Просмотр профиля пользователя."""
        serializer = CustomUserSerializer(
            request.user,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=['put', 'delete'],
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path='me/avatar',
        url_name='avatar'
    )
    def avatar(self, request):
        """Редактирование аватара."""
        instance = self.request.user
        if request.method == 'DELETE':
            instance.avatar = None
            instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AvatarSerializer(
            instance,
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(
        methods=['post', 'delete'],
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path=r'(?P<id>\d+)/subscribe',
        url_name='subscribe',
    )
    def subscribe(self, request, id):
        """Управление подпиской."""
        user = self.request.user
        following = get_object_or_404(CustomUser, id=id)
        if self.request.method == 'POST':
            serializer = CreateSubscriptionSerializer(
                data={
                    'user': user.id,
                    'following': following.id
                },
                context={
                    'request': request
                },
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(user=self.request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        unsubscribe, _ = Subscription.objects.filter(
            user=user,
            following=following,
        ).delete()
        if unsubscribe == 0:
            return Response(
                f'Подписка на {following.username} отсутствует',
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['get'],
        detail=False,
        permission_classes=[IsAuthenticated],
        url_path='subscriptions',
        url_name='subscriptions',
    )
    def get_subscriptions(self, request):
        """Получения списка подписок."""
        user = self.request.user
        subscribes = CustomUser.objects.filter(following__user=user)
        paginator = CustomPagination()
        result_pages = paginator.paginate_queryset(
            queryset=subscribes,
            request=request
        )
        serializer = ShowSubscriptionSerializer(
            result_pages,
            context={'request': request},
            many=True
        )
        return paginator.get_paginated_response(serializer.data)


class TagViewSet(
    viewsets.ReadOnlyModelViewSet
):
    """Вьюсет Тега."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(
    viewsets.ReadOnlyModelViewSet
):
    """Вьюсет Ингридиента."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = IngredientFilterSet
    search_fields = ('^name',)
    pagination_class = None


class RecipeViewSet(
    viewsets.ModelViewSet,
):
    """Вьюсет Рецепта."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilterSet

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return GetRecipeSerializer
        return CreateRecipeSerializer

    @action(
        methods=['get'],
        url_path='get-link',
        detail=True
    )
    def get_short_link(self, request, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        if not recipe.short_link:
            recipe.short_link = self.generate_short_link()
            recipe.save()
        return Response(
            {'short-link': recipe.short_link},
            status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        permission_classes=[IsAuthenticated],
        methods=['post', 'delete'],
        url_path=r'(?P<id>\d+)/favorite',
        url_name='favorite',
    )
    def add_recipe_to_favorite(self, request, id):
        """Добавление и удаление рецепта из избранного."""
        return self.add_recipe_to_favorite_or_cart(
            serializer=FavouriteRecipeSerializer,
            model=Recipe,
            rel_model=FavouriteRecipe,
            id=id,
            request=request
        )

    @action(
        detail=False,
        permission_classes=[IsAuthenticated],
        methods=['post', 'delete'],
        url_path=r'(?P<id>\d+)/shopping_cart',
        url_name='shopping_cart',
    )
    def add_recipe_to_shopping_cart(self, request, id):
        """Добавление и удаление рецепта в корзину покупок."""

        return self.add_recipe_to_favorite_or_cart(
            serializer=ShoppingCartRecipeSerializer,
            model=Recipe,
            rel_model=ShoppingList,
            id=id,
            request=request
        )

    def add_recipe_to_favorite_or_cart(
            self,
            serializer,
            model,
            id,
            request,
            rel_model
    ):
        recipe = get_object_or_404(model, id=id)
        user = self.request.user
        if self.request.method == 'POST':
            serializer = serializer(
                data={
                    'user': user.id,
                    'recipe': recipe.id
                },
                context={
                    'request': request
                }
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        recipe = rel_model.objects.filter(
            user=user, recipe=recipe
        )
        if not recipe:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        """Отправка файла со списком покупок."""
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_list__user=request.user
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            ingredient_amount=Sum('amount')
        ).order_by('ingredient__name')
        shopping_list = self.prepare_ingredients_for_download(ingredients)
        return self.download_ingredients(shopping_list)

    def prepare_ingredients_for_download(self, ingredients):
        shopping_list = ['Список покупок:\n']
        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            unit = ingredient['ingredient__measurement_unit']
            amount = ingredient['ingredient_amount']
            shopping_list.append(f'\n{name} - {amount}, {unit}')

        return shopping_list

    def download_ingredients(self, shopping_list):
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    def generate_short_link(self):
        """Генератор короткой ссылки."""
        while True:
            short_link = (
                URL + str(
                    uuid.uuid4()
                ).replace('-', '')[:SHORT_LINK_MAX_POSTFIX] + '/'
            )
            has_short_link = Recipe.objects.filter(
                short_link=short_link
            ).exists()
            if not has_short_link:
                break
        return short_link


def redirect_to_recipe_detail(request, short_link):
    """Редирект с короткой ссылки."""

    link = request.build_absolute_uri()
    recipe = get_object_or_404(Recipe, short_link=link)
    return redirect(
        'api.v1:recipe-detail',
        pk=recipe.id
    )
