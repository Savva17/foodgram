import json
from django.core.management.base import BaseCommand, CommandError
from recipes.models import Ingredient
from django.db.utils import IntegrityError


class Command(BaseCommand):
    help = 'Загружаем ингредиенты из файла "ingredients.json"'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path', nargs='?', default='ingredients.json', type=str
        )

    def handle(self, *args, **options):
        file_path = 'data/ingredients.json'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for ingredient in data:
                    try:
                        Ingredient.objects.create(
                            name=ingredient["name"],
                            measurement_unit=ingredient["measurement_unit"]
                        )
                    except IntegrityError:
                        print(
                            f'Ингридиет {ingredient["name"]} уже есть в базе'
                        )

            self.stdout.write(self.style.SUCCESS('Данные успешно загружены!'))
        except FileNotFoundError:
            raise CommandError('Файл отсутствует.')
