# # estate/signals.py
#
# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from django.db import transaction
# from .models import Customer, Property, Match
# from .utils_match import MatchManager
#
#
# @receiver(post_save, sender=Customer)
# def create_matches_on_customer_create(sender, instance, created, **kwargs):
#     """
#     وقتی مشتری جدید ثبت میشه، تطابق‌هایش با همه املاک ایجاد بشه
#     """
#     if created:
#         # اجرا در یک تراکنش جداگانه برای جلوگیری از قفل شدن
#         transaction.on_commit(
#             lambda: MatchManager.update_all_matches_for_customer(instance)
#         )
#
#
# @receiver(post_save, sender=Property)
# def create_matches_on_property_create(sender, instance, created, **kwargs):
#     """
#     وقتی ملک جدید ثبت میشه، تطابق‌هایش با همه مشتریان ایجاد بشه
#     """
#     if created:
#         transaction.on_commit(
#             lambda: MatchManager.update_all_matches_for_property(instance)
#         )
#
#
# @receiver(post_save, sender=Customer)
# def update_matches_on_customer_update(sender, instance, created, **kwargs):
#     """
#     وقتی مشتری بروزرسانی میشه (تغییر بودجه، منطقه، ...)
#     تطابق‌هایش بروزرسانی بشه
#     """
#     if not created:
#         # فقط اگر فیلدهای مهم تغییر کرده باشن
#         if hasattr(instance, '_changed_fields'):
#             important_fields = [
#                 'budget_min', 'budget_max', 'min_area', 'max_area',
#                 'min_rooms', 'max_rooms', 'customer_type'
#             ]
#             if any(f in instance._changed_fields for f in important_fields):
#                 transaction.on_commit(
#                     lambda: MatchManager.update_all_matches_for_customer(instance)
#                 )
#
#
# @receiver(post_save, sender=Property)
# def update_matches_on_property_update(sender, instance, created, **kwargs):
#     """
#     وقتی ملک بروزرسانی میشه (تغییر قیمت، امکانات، ...)
#     تطابق‌هایش بروزرسانی بشه
#     """
#     if not created:
#         if hasattr(instance, '_changed_fields'):
#             important_fields = [
#                 'price', 'area', 'rooms', 'contract_type',
#                 'property_type', 'status', 'rent_price', 'mortgage_price'
#             ]
#             if any(f in instance._changed_fields for f in important_fields):
#                 transaction.on_commit(
#                     lambda: MatchManager.update_all_matches_for_property(instance)
#                 )
#
#
# @receiver(post_delete, sender=Customer)
# def delete_matches_on_customer_delete(sender, instance, **kwargs):
#     """
#     وقتی مشتری حذف میشه، تطابق‌هایش هم حذف بشه
#     """
#     Match.objects.filter(customer=instance).delete()
#
#
# @receiver(post_delete, sender=Property)
# def delete_matches_on_property_delete(sender, instance, **kwargs):
#     """
#     وقتی ملک حذف میشه، تطابق‌هایش هم حذف بشه
#     """
#     Match.objects.filter(property=instance).delete()