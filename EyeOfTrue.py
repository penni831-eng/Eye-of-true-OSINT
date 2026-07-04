import re
import os
import requests
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ----- Конфиг -----
SOCIAL_SITES = [
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "tiktok.com",
    "github.com",
    "reddit.com",
    "twitch.tv",
    "linkedin.com",
    "t.me",
    "vk.com"
]

# hello bro
def choose_language():
    clear()
    print("Hi, select language / Привет,выбери язык:")
    print("1. English")
    print("2. Русский")
    choice = input("Enter 1 or 2 / Введите 1 или 2: ")
    return "en" if choice == "1" else "ru"

# it is visuals
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_logo(lang):
    purple = "\033[95m"
    reset = "\033[0m"
    white = "\033[97m"

    if lang == "en":
        title = "EYE OF TRUTH — OSINT TOOL v1.2"
        made = "Made by qarapin with ❤️"
    else:
        title = "ГЛАЗ ИСТИНЫ — OSINT ИНСТРУМЕНТ v1.2"
        made = "Сделано qarapin с ❤️"

    logo = f"""
    {purple}        █████████████████████████
    {purple}        █ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ █
    {purple}        █ ██ {white}▀▀▀▀▀▀▀▀▀▀▀{purple} ██ █
    {purple}        █ ██   {white}░░░░░  ░░░░░{purple}   ██ █
    {purple}        █ ██  {white}░ ███ ░░ ███ ░{purple}  ██ █
    {purple}        █ ██  {white}░ ███ ░░ ███ ░{purple}  ██ █
    {purple}        █ ██   {white}░░░░░  ░░░░░{purple}   ██ █
    {purple}        █ ██ ▄▄▄▄▄▄▄▄▄▄▄ ██ █
    {purple}        █ ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀ █
    {purple}        █████████████████████████
    {purple}
    {purple}       {white}{title}
    {purple}       {white}{made}
    {reset}
    """
    print(logo)

# ----- Сессия для ВК -----
def get_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    return session

def check_vk_username(username):
    session = get_session()
    url = f"https://vk.com/{username}"
    try:
        resp = session.get(url, timeout=5, allow_redirects=True)
        if resp.history:
            final_url = resp.url
            if "vk.com/feed" in final_url or "login" in final_url:
                return {"status": "not found", "link": None}
        if resp.status_code == 200:
            html = resp.text
            if f'page_id={username}' in html or f'id="{username}"' in html:
                return {"status": "found", "link": url}
            if re.search(r'"owner_id":-?\d+', html):
                return {"status": "found", "link": url}
            if '<title>' in html and not 'Ошибка' in html:
                return {"status": "found", "link": url}
        if resp.status_code == 404:
            return {"status": "not found", "link": None}
        if resp.status_code in [403, 429]:
            return {"status": "blocked", "link": url, "note": "ВК временно заблокировал запрос" if lang == "ru" else "VK temporarily blocked request"}
        return {"status": "unknown", "link": url}
    except Exception:
        return {"status": "error", "link": None}

# ----- Функции поиска -----
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return {"status": "invalid", "reason": "wrong format"}
    domain = email.split('@')[1]
    try:
        import dns.resolver
        mx = dns.resolver.resolve(domain, 'MX')
        return {"status": "valid", "mx": [str(r.exchange) for r in mx]}
    except Exception:
        return {"status": "valid", "mx": "MX lookup failed (no internet?)"}

def phone_lookup(phone):
    try:
        num = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(num):
            return {"error": "invalid number"}
        return {
            "valid": True,
            "country": geocoder.description_for_number(num, "en"),
            "carrier": carrier.name_for_number(num, "en"),
            "timezone": timezone.time_zones_for_number(num)
        }
    except Exception as e:
        return {"error": str(e)}

def search_username(username):
    results = {}
    for site in SOCIAL_SITES:
        if site == "vk.com":
            vk_data = check_vk_username(username)
            results[site] = {
                "status": vk_data.get("status", "error"),
                "link": vk_data.get("link")
            }
            continue

        url = f"https://{site}/{username}"
        try:
            resp = requests.get(url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                results[site] = {"status": "found", "link": url}
            else:
                results[site] = {"status": "not found", "link": None}
        except:
            results[site] = {"status": "timeout/error", "link": None}
    return results

def search_phone_by_vk(username):
    api_url = f"https://leakcheck.io/api/public?query={username}&type=username"
    try:
        resp = requests.get(api_url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("found"):
                return {"status": "found", "entries": data.get("entries", [])}
            else:
                return {"status": "not found", "message": "No data in leaks" if lang == "en" else "Нет данных в утечках"}
        else:
            return {"status": "error", "message": f"API returned code {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----- Меню -----
def menu(lang):
    clear()
    print_logo(lang)

    if lang == "en":
        print("\n=== MAIN MENU ===")
        print("1. Email search")
        print("2. Phone number lookup")
        print("3. Username search (social networks)")
        print("4. Find phone number by VK username (experimental)")
        print("5. Credits")
        print("0. Exit")
    else:
        print("\n=== ГЛАВНОЕ МЕНЮ ===")
        print("1. Поиск по Email")
        print("2. Поиск по номеру телефона")
        print("3. Поиск по username (соцсети)")
        print("4. Поиск номера телефона по username ВК (эксперимент)")
        print("5. Credits")
        print("0. Выход")

def credits(lang):
    clear()
    print_logo(lang)
    if lang == "en":
        print("\n=== CREDITS ===")
        print("Developer: qarapin")
        print("Idea, code, design — all made manually.")
        print("Purple eye — symbol of truth.")
        print("Version: 1.2")
    else:
        print("\n=== CREDITS ===")
        print("Разработчик: qarapin")
        print("Идея, код, дизайн — всё сделано вручную.")
        print("Фиолетовый глаз — символ истины.")
        print("Версия: 1.2")
    input("\nPress Enter to return to menu..." if lang == "en" else "\nНажми Enter, чтобы вернуться в меню...")

# ----- Основной цикл -----
def main():
    global lang
    lang = choose_language()

    while True:
        menu(lang)
        choice = input("Select action: " if lang == "en" else "Выберите действие: ")

        if choice == "0":
            print("Exiting..." if lang == "en" else "Выход...")
            break
        elif choice == "1":
            email = input("Enter email: " if lang == "en" else "Введите email: ")
            print("\n[Result]" if lang == "en" else "\n[Результат]")
            print(validate_email(email))
            input("\nPress Enter to continue..." if lang == "en" else "\nНажми Enter, чтобы продолжить...")
        elif choice == "2":
            phone = input("Enter phone number (+country code): " if lang == "en" else "Введите номер (+код страны): ")
            print("\n[Result]" if lang == "en" else "\n[Результат]")
            print(phone_lookup(phone))
            input("\nPress Enter to continue..." if lang == "en" else "\nНажми Enter, чтобы продолжить...")
        elif choice == "3":
            username = input("Enter username: " if lang == "en" else "Введите username: ")
            print("\n[Social media search]" if lang == "en" else "\n[Поиск по соцсетям]")
            results = search_username(username)
            for site, data in results.items():
                status = data.get("status", "unknown")
                link = data.get("link")
                if status == "found":
                    print(f"[+] {site}: found → {link}" if lang == "en" else f"[+] {site}: найден → {link}")
                elif status == "blocked":
                    print(f"[!] {site}: blocked (try later)" if lang == "en" else f"[!] {site}: заблокирован (попробуйте позже)")
                else:
                    print(f"[-] {site}: {status}")
            input("\nPress Enter to continue..." if lang == "en" else "\nНажми Enter, чтобы продолжить...")
        elif choice == "4":
            username = input("Enter VK username: " if lang == "en" else "Введите username ВК: ")
            print("\n[Searching phone via VK username]" if lang == "en" else "\n[Поиск номера по username ВК]")
            result = search_phone_by_vk(username)
            if result["status"] == "found":
                print(f"[+] Found entries: {len(result['entries'])}" if lang == "en" else f"[+] Найдено записей: {len(result['entries'])}")
                for entry in result["entries"]:
                    print(f"    - {entry}")
            else:
                print(f"[-] {result.get('message', 'Unknown error')}" if lang == "en" else f"[-] {result.get('message', 'Неизвестная ошибка')}")
            input("\nPress Enter to continue..." if lang == "en" else "\nНажми Enter, чтобы продолжить...")
        elif choice == "5":
            credits(lang)
        else:
            print("Invalid input." if lang == "en" else "Неверный ввод.")
            input("Press Enter..." if lang == "en" else "Нажми Enter...")

if __name__ == "__main__":
    main()