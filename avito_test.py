from curl_cffi import requests

url = "https://www.avito.ru/omsk?q=видеокарта"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}

print("🔎 Запрашиваю Avito...")

try:
    response = requests.get(
        url,
        headers=headers,
        impersonate="chrome",
        timeout=30,
    )

    print("HTTP:", response.status_code)
    print("Размер ответа:", len(response.text))

    print("\nПервые 500 символов:")
    print(response.text[:500])

except Exception as e:
    print("❌ ОШИБКА:")
    print(repr(e))