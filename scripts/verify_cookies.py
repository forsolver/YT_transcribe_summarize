#!/usr/bin/env python3
"""Проверяет cookies-файл для работы youtube-transcript-api.

Запуск:
    python scripts/verify_cookies.py [cookies_path]
Если путь не указан, используется cookies.txt в текущей директории.
"""
import sys
import os
import http.cookiejar as cookielib
from urllib.parse import urlparse

REQUIRED_COOKIES = {
    'SID', 'HSID', 'SSID', 'APISID', 'SAPISID',
    'LOGIN_INFO', 'YSC', 'VISITOR_INFO1_LIVE', 'PREF'
}

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'cookies.txt'
    if not os.path.exists(path):
        print('Файл не найден:', path)
        sys.exit(1)

    cj = cookielib.MozillaCookieJar()
    try:
        cj.load(path, ignore_discard=True, ignore_expires=True)
    except Exception as e:
        print('Не удалось прочитать cookies (ожидался формат Netscape).', e)
        sys.exit(1)

    youtube_cookies = [c for c in cj if 'youtube.com' in c.domain]
    print(f'Всего cookies: {len(cj)}, из них для youtube.com: {len(youtube_cookies)}')
    names = {c.name for c in youtube_cookies}
    missing = REQUIRED_COOKIES - names
    if missing:
        print('Не найдены важные куки:', ', '.join(sorted(missing)))
    else:
        print('Все ключевые куки присутствуют.')

    # Базовый тест: сформируем заголовок cookie для youtube
    sample_header = '; '.join(f"{c.name}={c.value}" for c in youtube_cookies if not c.is_expired())
    print('Пример заголовка Cookie (усечён):', sample_header[:120] + '...' if len(sample_header) > 120 else sample_header)

if __name__ == '__main__':
    main() 