"""
One-shot setup: migrate + collectstatic + ensure superuser. Idempotent.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

SUPERUSER_EMAIL = "admin@agentic.company"
SUPERUSER_PASSWORD = "change-me"


class Command(BaseCommand):
    help = "Run migrate + collectstatic + ensure superuser. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--skip-superuser", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Running migrations..."))
        call_command("migrate", "--noinput", stdout=self.stdout)

        self.stdout.write(self.style.MIGRATE_HEADING("Collecting static files..."))
        call_command("collectstatic", "--noinput", stdout=self.stdout)

        if options["skip_superuser"]:
            self.stdout.write("Skipping superuser.")
            return

        from accounts.models import User
        if User.objects.filter(email=SUPERUSER_EMAIL).exists():
            self.stdout.write(f"Superuser {SUPERUSER_EMAIL} already exists — skipping.")
            return

        User.objects.create_superuser(email=SUPERUSER_EMAIL, password=SUPERUSER_PASSWORD)
        self.stdout.write(self.style.SUCCESS(f"Created superuser: {SUPERUSER_EMAIL}"))
