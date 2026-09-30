# dynamicform/management/commands/seed_inputs.py

from django.core.management.base import BaseCommand
from dynamicform.models import InputTemplate

class Command(BaseCommand):
    help = 'ایجاد نمونه اینپوت‌های اولیه'

    def handle(self, *args, **options):
        input_types = [
            ('text', 'متن کوتاه'),
            ('textarea', 'متن بلند'),
            ('number', 'عدد'),
            ('email', 'ایمیل'),
            ('phone', 'تلفن'),
            ('date', 'تاریخ'),
            ('datetime', 'تاریخ و زمان'),
            ('time', 'ساعت'),
            ('select', 'انتخاب از لیست'),
            ('checkbox', 'چک‌باکس'),
            ('radio', 'دکمه رادیویی'),
            ('file', 'فایل'),
            ('image', 'تصویر'),
            ('url', 'لینک'),
            ('color', 'رنگ'),
            ('password', 'رمز عبور'),
        ]

        for input_type, title in input_types:
            obj, created = InputTemplate.objects.get_or_create(
                input_type=input_type,
                defaults={
                    'css_class': 'form-control',
                    'wrapper_class': 'mb-3',
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ {title} ایجاد شد'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️ {title} از قبل وجود دارد'))