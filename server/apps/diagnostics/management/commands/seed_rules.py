from django.core.management.base import BaseCommand

from apps.diagnostics.runner import seed_builtin_rules


class Command(BaseCommand):
    help = "Seed or update built-in diagnostic rules"

    def handle(self, *args, **options):
        seed_builtin_rules()
        self.stdout.write(self.style.SUCCESS("Built-in diagnostic rules seeded."))
