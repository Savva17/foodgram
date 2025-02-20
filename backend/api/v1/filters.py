from django_filters.rest_framework import (
    AllValuesMultipleFilter,
    BooleanFilter, CharFilter,
    FilterSet
)

from recipes.models import Ingredient, Recipe


class IngredientFilterSet(FilterSet):
    """Фильтр для Ингредиентов."""

    name = CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilterSet(FilterSet):
    """Фильтр для Рецептов."""

    tags = AllValuesMultipleFilter(
        field_name='tags__slug',
        lookup_expr='contains',
    )

    is_favorited = BooleanFilter(
        method='get_is_favorited'
    )
    is_in_shopping_cart = BooleanFilter(
        method='get_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart')

    def get_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(favourite__user=self.request.user)
        return queryset

    def get_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(shopping_list__user=self.request.user)
        return queryset
