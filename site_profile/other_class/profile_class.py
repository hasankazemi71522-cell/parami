from django.core.files.uploadedfile import InMemoryUploadedFile
from datetime import datetime
from django.http import JsonResponse
# from .models import Commodity, get_filename_ext
import requests
import json
import ghasedak
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile


def three_digits(num):
    num = str(num)
    num_list = []
    for obj in num:
        num_list.append(obj)
    num_character = len(num)
    number_part = num_character // 3
    number_left = num_character % 3
    if number_left == 0:
        number_left = 3
        number_part = number_part - 1
    if num_character > 3:
        for i in range(number_part):
            num_list.insert(number_left, ",")
            number_left += 4
    num_result = "".join(num_list)
    return num_result

