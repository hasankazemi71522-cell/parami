# case_management/utils.py

import jdatetime
from datetime import datetime
from django.utils import timezone


def jalali_to_gregorian(date_str):
    """
    تبدیل تاریخ شمسی (رشته‌ای) به میلادی
    فرمت ورودی: "1402/10/15 14:30"
    خروجی: datetime object (timezone-aware)
    """
    if not date_str:
        return None

    date_str = date_str.strip()
    try:
        # جداسازی تاریخ و زمان
        parts = date_str.split(' ')
        date_part = parts[0]  # 1402/10/15
        time_part = parts[1] if len(parts) > 1 else '00:00'

        year, month, day = map(int, date_part.split('/'))
        hour, minute = map(int, time_part.split(':'))

        gregorian_date = jdatetime.date(year, month, day).togregorian()
        result = datetime(
            gregorian_date.year,
            gregorian_date.month,
            gregorian_date.day,
            hour,
            minute
        )
        return timezone.make_aware(result) if timezone.is_naive(result) else result

    except Exception as e:
        raise ValueError(f"فرمت تاریخ نامعتبر است. فرمت صحیح: سال/ماه/روز ساعت:دقیقه (مثال: 1402/10/15 14:30)")


def jalali_to_gregorian_parts(year, month, day, hour=0, minute=0):
    """
    تبدیل تاریخ شمسی (با اجزای جداگانه) به میلادی
    برای استفاده در صورت دریافت فیلدهای جداگانه از فرم
    """
    try:
        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour or 0)
        minute = int(minute or 0)

        gregorian_date = jdatetime.date(year, month, day).togregorian()
        result = datetime(
            gregorian_date.year,
            gregorian_date.month,
            gregorian_date.day,
            hour,
            minute
        )
        return timezone.make_aware(result) if timezone.is_naive(result) else result

    except Exception as e:
        raise ValueError(f"تاریخ نامعتبر: {e}")


def gregorian_to_jalali(datetime_obj):
    """
    تبدیل تاریخ میلادی به شمسی برای نمایش
    خروجی: رشته با فرمت "1402/10/15 14:30"
    """
    if not datetime_obj:
        return ''

    if timezone.is_aware(datetime_obj):
        datetime_obj = timezone.make_naive(datetime_obj)

    jalali_date = jdatetime.date.fromgregorian(
        year=datetime_obj.year,
        month=datetime_obj.month,
        day=datetime_obj.day
    )
    return f"{jalali_date.year}/{jalali_date.month:02d}/{jalali_date.day:02d} {datetime_obj.hour:02d}:{datetime_obj.minute:02d}"