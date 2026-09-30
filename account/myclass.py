from datetime import datetime
from django.http import JsonResponse
import requests
import json
import ghasedak


def send_message_signup(fullname, mobile, password):
    url = "https://api.ghasedak.me/v2/verification/send/simple"
    payload = f"receptor={mobile}&template=signupparami&type=1&param1={fullname}&param2={mobile}&param3={password}"
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'apikey': "70d9543e8a8de069edac29e86d06b4f4a644c729a36b7a86b946f2e0116efbae",
        'cache-control': "no-cache",
    }
    requests.request("POST", url, data=payload.encode('utf-8'), headers=headers)


def send_message_login(mobile, random_msg):
    url = "https://api.ghasedak.me/v2/verification/send/simple"
    payload = f"receptor={mobile}&template=loginparami&type=1&param1={random_msg}"
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'apikey': "70d9543e8a8de069edac29e86d06b4f4a644c729a36b7a86b946f2e0116efbae",
        'cache-control': "no-cache",
    }
    requests.request("POST", url, data=payload.encode('utf-8'), headers=headers)


def send_message_new_task(mobile, fullname):
    url = "https://api.ghasedak.me/v2/verification/send/simple"
    payload = f"receptor={mobile}&template=sendtask&type=1&param1={fullname}"
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'apikey': "70d9543e8a8de069edac29e86d06b4f4a644c729a36b7a86b946f2e0116efbae",
        'cache-control': "no-cache",
    }
    requests.request("POST", url, data=payload.encode('utf-8'), headers=headers)


def new_income(mobile, fullname, old_wallet, new_wallet):
    url = "https://api.ghasedak.me/v2/verification/send/simple"
    payload = f"receptor={mobile}&template=newincome&type=1&param1={fullname}&param2={old_wallet}&param3={new_wallet}"
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'apikey': "70d9543e8a8de069edac29e86d06b4f4a644c729a36b7a86b946f2e0116efbae",
        'cache-control': "no-cache",
    }
    requests.request("POST", url, data=payload.encode('utf-8'), headers=headers)


def new_cart(mobile, fullname, user_mobile):
    url = "https://api.ghasedak.me/v2/verification/send/simple"
    payload = f"receptor={mobile}&template=newcart&type=1&param1={fullname}&param2={user_mobile}"
    headers = {
        'content-type': "application/x-www-form-urlencoded",
        'apikey': "70d9543e8a8de069edac29e86d06b4f4a644c729a36b7a86b946f2e0116efbae",
        'cache-control': "no-cache",
    }
    requests.request("POST", url, data=payload.encode('utf-8'), headers=headers)




def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if (gm > 2):
        gy2 = gy + 1
    else:
        gy2 = gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if (days > 365):
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if (days < 186):
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return [jy, jm, jd]



def edit_miladi_shamsi(date):
    jalali = gregorian_to_jalali(date.year, date.month, date.day)
    jalali_y = datetime(int(jalali[0]), int(jalali[1]), int(jalali[2])).date()
    return jalali_y

