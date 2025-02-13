# import django_filters
# from recipes.models import Recipe, Tag


# class RecipeFilter(django_filters.FilterSet):
#     is_favorited = django_filters.NumberFilter(
#         method='filter_is_favorited')
#     is_in_shopping_cart = django_filters.NumberFilter(
#         method='filter_is_in_shopping_cart')
#     author = django_filters.NumberFilter(field_name='author__id')
#     tags = django_filters.ModelMultipleChoiceFilter(
#         field_name='tags__slug',
#         to_field_name='slug',
#         queryset=Tag.objects.all()
#     )

#     class Meta:
#         model = Recipe
#         fields = ['is_favorited', 'is_in_shopping_cart', 'author', 'tags']

#     def filter_is_favorited(self, queryset, name, value):
#         if value == 1 and self.request.user.is_authenticated:
#             return queryset.filter(favorited_by__user=self.request.user)
#         return queryset

#     def filter_is_in_shopping_cart(self, queryset, name, value):
#         if value == 1 and self.request.user.is_authenticated:
#             return queryset.filter(in_shopping_list__user=self.request.user)
#         return queryset

