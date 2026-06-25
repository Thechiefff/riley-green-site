import requests
from django.conf import settings


def send_telegram(message: str, image_path: str = None) -> bool:
    try:
        if image_path:
            with open(image_path, 'rb') as img:
                resp = requests.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data={'chat_id': settings.TELEGRAM_CHAT_ID, 'caption': message, 'parse_mode': 'Markdown'},
                    files={'photo': img},
                    timeout=15,
                )
            return resp.ok
        resp = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={'chat_id': settings.TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'},
            timeout=8,
        )
        return resp.ok
    except Exception:
        return False


def send_telegram_photo(image_path: str, caption: str) -> bool:
    """Send a photo with caption to the owner's Telegram chat."""
    return send_telegram(caption, image_path)
