# case_management/management/commands/check_deadlines.py

from django.core.management.base import BaseCommand
from case_management.utils import check_and_create_deadline_alerts


class Command(BaseCommand):
    help = 'بررسی مهلت‌های فرآیندها و ارسال اخطار به سرپرستان'

    def handle(self, *args, **options):
        self.stdout.write('🔄 در حال بررسی مهلت‌های فرآیندها...')
        alerts = check_and_create_deadline_alerts()
        self.stdout.write(self.style.SUCCESS(f'✅ {len(alerts)} اخطار جدید ایجاد شد.'))