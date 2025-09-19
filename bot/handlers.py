from __future__ import annotations
import asyncio
import logging
from typing import Optional, Tuple, List
from datetime import datetime

from telegram import Update, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    Application,
    filters,
)
from telegram.request import HTTPXRequest

from db import init_db, upsert_user, get_user
from bot.keyboards import (
    lang_reply_keyboard,
    contact_keyboard,
    location_request_keyboard,
    categories_keyboard,
    place_card_buttons,
    categories_reply_keyboard,
    settings_keyboard,          # NEW: import
)
from bot.locale import L
from services.google_places import search_nearby, search_text, get_photo_url
from services.google_places import reverse_geocode
from services.utils import haversine_km  # NEW: for distance
from config import TELEGRAM_BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Conversation states (expanded) ─────────────────────────────────────────────
(LANG, FIRST_NAME, LAST_NAME, CONTACT,
 WAIT_LOCATION_OR_TEXT, CHOOSE_CATEGORY,
 SETTINGS, EDIT_NAME, EDIT_PHONE) = range(9)

# Updated canonical categories: 4 items
ENG_CATEGORIES: List[str] = [
    "Restaurant",
    "Hotel",
    "Park",
    "Historic Places",
]

def get_lang(tg_id: int, default: str = "en") -> str:
    row = get_user(tg_id)
    if row and row[2]:
        return row[2]
    return default

def _category_items_for_lang(lang: str):
    localized = L["categories"][lang]
    pairs = []
    for i, label in enumerate(localized):
        key = ENG_CATEGORIES[i] if i < len(ENG_CATEGORIES) else localized[i]
        pairs.append((label, key))
    return pairs

# NEW: distance formatter
def _fmt_distance_km(dkm: float) -> str:
    if dkm < 1.0:
        return f"{int(dkm * 1000)} m"
    if dkm < 10:
        return f"{dkm:.1f} km"
    return f"{int(round(dkm))} km"

# NEW: take today's hours line from weekdayDescriptions if present
def _today_hours_line(weekday_descriptions: List[str]) -> Optional[str]:
    if not weekday_descriptions:
        return None
    idx = datetime.utcnow().weekday()  # Approximation (no place TZ)
    wanted_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if 0 <= idx <= 6:
        name = wanted_names[idx]
        for line in weekday_descriptions:
            if line.startswith(name + ":") or line.startswith(name + " :"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
                return line
    return weekday_descriptions[0]

# ── Registration & main flow ──────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    user = update.effective_user
    # Check if user already registered
    row = get_user(user.id)
    if row:
        _id, _tg, language, first_name, last_name, phone = row
        # Consider registered if language, first_name, last_name, and phone are present
        if language and first_name and last_name and phone:
            lang = language
            await update.message.reply_text(
                L["ask_location_or_text"][lang],
                reply_markup=location_request_keyboard(
                    L["send_location_button"][lang],
                    L["type_place_button"][lang],
                    settings_text=L["settings_button"][lang],   # NEW
                ),
            )
            return WAIT_LOCATION_OR_TEXT
    # Not registered yet → ensure user record exists and start registration flow
    upsert_user(user.id)
    await update.message.reply_text(L["lang_prompt"]["en"], reply_markup=lang_reply_keyboard())
    return LANG

async def on_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").lower()
    mapping = {
        "oʻzbekcha": "uz", "ozbekcha": "uz", "uzbek": "uz", "🇺🇿 oʻzbekcha": "uz",
        "русский": "ru", "russian": "ru", "🇷🇺 русский": "ru",
        "english": "en", "🇬🇧 english": "en",
    }
    lang = next((v for k, v in mapping.items() if k in txt), "en")
    upsert_user(update.effective_user.id, language=lang)
    await update.message.reply_text(L["ask_name"][lang], reply_markup=ReplyKeyboardRemove())
    return FIRST_NAME

async def on_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    upsert_user(update.effective_user.id, first_name=update.message.text.strip())
    await update.message.reply_text(L["ask_surname"][lang])
    return LAST_NAME

async def on_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    upsert_user(update.effective_user.id, last_name=update.message.text.strip())
    await update.message.reply_text(L["ask_contact"][lang], reply_markup=contact_keyboard(L["share_phone_button"][lang]))
    return CONTACT

async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    phone = update.message.contact.phone_number if update.message.contact else update.message.text.strip()
    upsert_user(update.effective_user.id, phone=phone)
    await update.message.reply_text(
        L["ask_location_or_text"][lang],
        reply_markup=location_request_keyboard(
            L["send_location_button"][lang],
            L["type_place_button"][lang],
            settings_text=L["settings_button"][lang],   # NEW
        ),
    )
    return WAIT_LOCATION_OR_TEXT

async def on_location_or_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    text_in = (update.message.text or "").strip()

    # If user tapped "Settings" on reply keyboard, open settings menu
    if text_in == L["settings_button"][lang]:
        return await settings_entry(update, context)

    context.user_data["query_point"] = None

    if update.message.location:
        context.user_data["query_point"] = (update.message.location.latitude, update.message.location.longitude)
    else:
        typed = text_in
        coords: Optional[Tuple[float, float]] = await asyncio.to_thread(search_text, typed)
        if not coords:
            await update.message.reply_text(L["no_results"][lang])
            return WAIT_LOCATION_OR_TEXT
        context.user_data["query_point"] = coords

    lat, lng = context.user_data["query_point"]
    # Reverse geocode for address (localized)
    addr = await asyncio.to_thread(reverse_geocode, lat, lng, lang)

    # 1) Prompt with address in one line
    if addr:
        await update.message.reply_text(f"{L['you_are_here'][lang]} {addr}")
    else:
        await update.message.reply_text(f"{L['you_are_here'][lang]} {lat:.5f}, {lng:.5f}")

    # 2) Location bubble (map preview)
    try:
        await update.message.reply_location(latitude=lat, longitude=lng)
    except Exception:
        pass

    # 3) Ask what to search and show ReplyKeyboard categories
    labels = L["categories"][lang]
    await update.message.reply_text(
        L["what_search"][lang],
        reply_markup=categories_reply_keyboard(labels, L["back"][lang]),
    )
    return CHOOSE_CATEGORY

async def on_choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    text = (update.callback_query.data if update.callback_query else update.message.text).strip() if update else ""

    # Handle Back via reply keyboard
    if text == L["back"][lang] or (update.callback_query and text == "back_root"):
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            L["ask_location_or_text"][lang],
            reply_markup=location_request_keyboard(
                L["send_location_button"][lang],
                L["type_place_button"][lang],
                settings_text=L["settings_button"][lang],   # NEW
            ),
        )
        return WAIT_LOCATION_OR_TEXT

    # Map localized label to canonical key by position
    items = _category_items_for_lang(lang)
    label_to_key = {label: key for label, key in items}

    # If came from inline callback
    if update.callback_query and text.startswith("cat|"):
        _, category_key = text.split("|", 1)
    else:
        category_key = label_to_key.get(text)
        if not category_key:
            return CHOOSE_CATEGORY

    lat, lng = context.user_data.get("query_point", (None, None))
    if lat is None:
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            L["ask_location_or_text"][lang],
            reply_markup=location_request_keyboard(
                L["send_location_button"][lang],
                L["type_place_button"][lang],
                settings_text=L["settings_button"][lang],   # NEW
            ),
        )
        return WAIT_LOCATION_OR_TEXT

    await (update.callback_query.message if update.callback_query else update.message).reply_text(L["searching"][lang])

    places = await asyncio.to_thread(search_nearby, lat, lng, category_key)

    if not places:
        labels = L["categories"][lang]
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            L["no_results"][lang], reply_markup=categories_reply_keyboard(labels, L["back"][lang])
        )
        return CHOOSE_CATEGORY

    # Render cards with: photo, name, opening + today's hours, distance, phone, website, address
    for p in places:
        name = (p.get("displayName") or {}).get("text", "—")
        addr = p.get("formattedAddress", "—")
        loc = p.get("location", {}) or {}
        plat = loc.get("latitude")
        plng = loc.get("longitude")
        rating = p.get("rating")
        urc = p.get("userRatingCount")
        hours = p.get("currentOpeningHours") or {}
        open_now = hours.get("openNow")
        weekday_desc = hours.get("weekdayDescriptions") or []

        phone = p.get("internationalPhoneNumber") or p.get("nationalPhoneNumber")
        website = p.get("websiteUri")
        maps_uri = p.get("googleMapsUri")

        # Distance
        dist_line = ""
        if plat is not None and plng is not None and lat is not None:
            dkm = haversine_km(lat, lng, plat, plng)
            dist_line = f" • { _fmt_distance_km(dkm) } away"

        # Hours
        today_line = _today_hours_line(weekday_desc)
        hours_line = None
        if open_now is not None and today_line:
            hours_line = ("🟢 Open now" if open_now else "🔴 Closed now") + f" • {today_line}"
        elif open_now is not None:
            hours_line = "🟢 Open now" if open_now else "🔴 Closed now"
        elif today_line:
            hours_line = today_line

        # Photo
        photo_url = None
        photos = p.get("photos") or []
        if photos:
            photo_name = photos[0].get("name")
            if photo_name:
                photo_url = await asyncio.to_thread(get_photo_url, photo_name)

        # Build caption
        lines = [f"<b>{name}</b>"]
        if rating:
            lines.append(f"⭐ {rating} ({urc or 0}){dist_line}")
        else:
            if dist_line:
                lines.append(dist_line.strip(" •"))
        if hours_line:
            lines.append(hours_line)
        lines.append(f"📍 {addr}")
        if phone:
            lines.append(f"📞 {phone}")
        # Website (fallback to Google Maps page)
        if website:
            lines.append(f'🌐 <a href="{website}">Website</a>')
        elif maps_uri:
            lines.append(f'🌐 <a href="{maps_uri}">Google Maps Page</a>')

        caption = "\n".join(lines)

        if photo_url:
            await (update.callback_query.message if update.callback_query else update.message).reply_photo(
                photo=photo_url,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=place_card_buttons(plat, plng, L["back"][lang]),
            )
        else:
            await (update.callback_query.message if update.callback_query else update.message).reply_text(
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=place_card_buttons(plat, plng, L["back"][lang]),
            )

    labels = L["categories"][lang]
    await (update.callback_query.message if update.callback_query else update.message).reply_text(
        L["choose_category"][lang], reply_markup=categories_reply_keyboard(labels, L["back"][lang])
    )
    return CHOOSE_CATEGORY

# ── Settings flow ─────────────────────────────────────────────────────────────
async def settings_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    # Can be entered via /settings command or "⚙️ Settings" button
    if update.message:
        await update.message.reply_text(
            L["settings_title"][lang],
            reply_markup=settings_keyboard(
                L["edit_name"][lang],
                L["edit_phone"][lang],
                L["back"][lang],
            ),
        )
    else:
        await update.callback_query.message.reply_text(
            L["settings_title"][lang],
            reply_markup=settings_keyboard(
                L["edit_name"][lang],
                L["edit_phone"][lang],
                L["back"][lang],
            ),
        )
    return SETTINGS

async def on_settings_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    choice = (update.message.text or "").strip()

    if choice == L["back"][lang]:
        await update.message.reply_text(
            L["ask_location_or_text"][lang],
            reply_markup=location_request_keyboard(
                L["send_location_button"][lang],
                L["type_place_button"][lang],
                settings_text=L["settings_button"][lang],
            ),
        )
        return WAIT_LOCATION_OR_TEXT

    if choice == L["edit_name"][lang]:
        await update.message.reply_text(L["enter_new_name"][lang], reply_markup=ReplyKeyboardRemove())
        return EDIT_NAME

    if choice == L["edit_phone"][lang]:
        await update.message.reply_text(L["enter_new_phone"][lang], reply_markup=ReplyKeyboardRemove())
        return EDIT_PHONE

    # Unknown tap → stay in SETTINGS
    await update.message.reply_text(L["settings_title"][lang],
        reply_markup=settings_keyboard(L["edit_name"][lang], L["edit_phone"][lang], L["back"][lang]))
    return SETTINGS

async def on_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    full = (update.message.text or "").strip()
    # Accept either full name or just first name; split safely
    parts = full.split()
    if len(parts) >= 2:
        first, last = parts[0], " ".join(parts[1:])
    else:
        first, last = full, None
    upsert_user(update.effective_user.id, first_name=first, last_name=last)
    await update.message.reply_text(
        L["saved"][lang],
        reply_markup=settings_keyboard(L["edit_name"][lang], L["edit_phone"][lang], L["back"][lang]),
    )
    return SETTINGS

async def on_edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    phone = (update.message.text or "").strip()
    upsert_user(update.effective_user.id, phone=phone)
    await update.message.reply_text(
        L["saved"][lang],
        reply_markup=settings_keyboard(L["edit_name"][lang], L["edit_phone"][lang], L["back"][lang]),
    )
    return SETTINGS

# ── Errors & misc ────────────────────────────────────────────────────────────
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Exception while handling an update", exc_info=context.error)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text("⚠️ An error occurred. Please try again.")
    except Exception:
        pass

def build_app() -> Application:
    # Increase network timeouts to reduce TimedOut errors on slow networks
    request = HTTPXRequest(
        connection_pool_size=20,
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=10.0,
    )
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request)
        .build()
    )
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("restart", start),
            CommandHandler("settings", settings_entry),  # NEW: allow /settings
        ],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_language)],
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_last_name)],
            CONTACT: [
                MessageHandler(filters.CONTACT, on_contact),
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_contact),
            ],
            WAIT_LOCATION_OR_TEXT: [
                MessageHandler(filters.LOCATION, on_location_or_text),
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_location_or_text),
            ],
            CHOOSE_CATEGORY: [
                # Accept both reply keyboard texts and legacy inline callbacks
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_choose_category),
                CallbackQueryHandler(on_choose_category, pattern=r"^(cat\|.+|back_root)$"),
            ],
            # NEW settings states:
            SETTINGS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_settings_choice),
            ],
            EDIT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_edit_name),
            ],
            EDIT_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, on_edit_phone),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
        per_message=True,
    )
    app.add_handler(conv)
    app.add_error_handler(error_handler)
    return app

async def on_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.id)
    await update.message.reply_text(
        L["ask_location_or_text"][lang] + f"\n\n/{'settings'} — {L['settings_shortcut_hint'][lang]}"
    )

def main():
    app = build_app()
    app.add_handler(MessageHandler(filters.COMMAND, on_unknown))
    # Drop pending updates to avoid long backlog and reduce timeouts
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
