# bot/keyboards.py
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from typing import List, Tuple


def lang_reply_keyboard():
    """Language selection via ReplyKeyboardMarkup (NOT inline)."""
    kb = [
        [KeyboardButton("🇺🇿 Oʻzbekcha")],
        [KeyboardButton("🇷🇺 Русский")],
        [KeyboardButton("🇬🇧 English")],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)


def contact_keyboard(text_label: str):
    """Share phone via contact request button."""
    kb = [[KeyboardButton(text_label, request_contact=True)]]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True)


def location_request_keyboard(send_location_text: str, type_place_text: str, settings_text: str | None = None):
    """
    Keyboard for sending live location or typing an address/place.
    Optionally adds a 'Settings' button on a new row.
    """
    kb = [
        [KeyboardButton(send_location_text, request_location=True)],
        # If you also want a text-input mode button on the reply keyboard, uncomment:
        # [KeyboardButton(type_place_text)],
    ]
    if settings_text:
        kb.append([KeyboardButton(settings_text)])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def categories_keyboard(items: List[Tuple[str, str]], back_text: str):
    """
    Inline categories.
    items: list of (label_to_show, canonical_key) tuples.
    We keep localized label but use canonical English key in callback_data.
    """
    rows = []
    for label, key in items:
        rows.append([InlineKeyboardButton(label, callback_data=f"cat|{key}")])
    rows.append([InlineKeyboardButton(back_text, callback_data="back_root")])
    return InlineKeyboardMarkup(rows)


def categories_reply_keyboard(labels: List[str], back_text: str):
    """ReplyKeyboard with category labels (one per row) and a Back button."""
    kb: List[List[KeyboardButton]] = [[KeyboardButton(lbl)] for lbl in labels]
    kb.append([KeyboardButton(back_text)])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)


def place_card_buttons(lat: float, lng: float, back_text: str):
    """Inline buttons for external navigation + back to categories."""
    gmaps = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"
    ymaps = f"https://yandex.com/maps/?rtext=~{lat},{lng}&rtt=auto"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Google Maps ▶️", url=gmaps)],
            [InlineKeyboardButton("Yandex Maps ▶️", url=ymaps)],
            [InlineKeyboardButton(back_text, callback_data="back_root")],
        ]
    )


# NEW: simple settings menu (reply keyboard) with language at the top
def settings_keyboard(edit_language_label: str, edit_name_label: str, edit_phone_label: str, back_text: str):
    kb = [
        [KeyboardButton(edit_language_label)],
        [KeyboardButton(edit_name_label)],
        [KeyboardButton(edit_phone_label)],
        [KeyboardButton(back_text)],
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)
