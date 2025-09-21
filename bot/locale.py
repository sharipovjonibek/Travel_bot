# bot/locale.py
# Simple i18n dict with visual icons (UZ/RU/EN)
L = {
    'lang_prompt': {
        'uz': "🌐 Tilni tanlang:",
        'ru': "🌐 Выберите язык:",
        'en': "🌐 Choose a language:",
    },

    'ask_name': {
        'uz': "👤 Ismingizni kiriting:",
        'ru': "👤 Введите ваше имя:",
        'en': "👤 Please enter your first name:",
    },

    'ask_surname': {
        'uz': "🧾 Familiyangizni kiriting:",
        'ru': "🧾 Введите вашу фамилию:",
        'en': "🧾 Please enter your surname:",
    },

    'ask_contact': {
        'uz': "📞 Telefon raqamingizni yuboring (tugma orqali) yoki yozing:",
        'ru': "📞 Отправьте номер (кнопкой) или введите вручную:",
        'en': "📞 Send your phone number (button) or type it:",
    },

    'share_phone_button': {
        'uz': "📲 Raqamni ulashish",
        'ru': "📲 Поделиться номером",
        'en': "📲 Share phone",
    },

    'ask_location_or_text': {
        'uz': "📍 Lokatsiyani yuboring yoki manzil/joy nomini yozing.\n\nMisollar:\n- \"Ziyolilar 9, Toshkent\"\n- \"Registon, Samarqand\"\n- \"Jizzax shahri\"",
        'ru': "📍 Отправьте геолокацию или введите адрес/место.\n\nПримеры:\n- \"ул. Зиёлилар 9, Ташкент\"\n- \"Регистан, Самарканд\"\n- \"город Джизак\"",
        'en': "📍 Send your location or type an address/place.\n\nExamples:\n- \"Ziyolilar 9, Tashkent\"\n- \"Registan, Samarkand\"\n- \"Jizzakh city\"",
    },

    'you_are_here': {
        'uz': "📌 Siz hozir shu joydasiz:",
        'ru': "📌 Вы сейчас здесь:",
        'en': "📌 You are here:",
    },

    'what_search': {
        'uz': "🔎 Nimani qidiramiz?",
        'ru': "🔎 Что будем искать?",
        'en': "🔎 What do you want to search for?",
    },

    # Buttons for choosing input mode
    'send_location_button': {
        'uz': "📍 Lokatsiyani yuborish",
        'ru': "📍 Отправить геолокацию",
        'en': "📍 Send location",
    },
    'type_place_button': {
        'uz': "⌨️ Manzil/joy nomini yozish",
        'ru': "⌨️ Ввести адрес/место",
        'en': "⌨️ Type address/place",
    },

    'choose_category': {
        'uz': "🗂️ Kategoriya tanlang:",
        'ru': "🗂️ Выберите категорию:",
        'en': "🗂️ Choose a category:",
    },

    'categories': {
        'uz': ["🍽️ Restoran", "🏨 Mehmonxona", "🌳 Park", "🏛️ Tarixiy joylar"],
        'ru': ["🍽️ Рестораны", "🏨 Отели", "🌳 Парки", "🏛️ Исторические места"],
        'en': ["🍽️ Restaurants", "🏨 Hotels", "🌳 Parks", "🏛️ Historical places"],
    },

    'back': {
        'uz': "⬅️ Orqaga",
        'ru': "⬅️ Назад",
        'en': "⬅️ Back",
    },

    'searching': {
        'uz': "🔄 Qidirilmoqda…",
        'ru': "🔄 Ищу…",
        'en': "🔄 Searching…",
    },

    'no_results': {
        'uz': "🙈 Hech narsa topilmadi.",
        'ru': "🙈 Ничего не найдено.",
        'en': "🙈 No results found.",
    },

    'send_more': {
        'uz': "➡️ Yana natijalar",
        'ru': "➡️ Ещё результаты",
        'en': "➡️ More results",
    },

    # Settings
    'settings_button': {
        'uz': "⚙️ Sozlamalar",
        'ru': "⚙️ Настройки",
        'en': "⚙️ Settings",
    },
    'settings_title': {
        'uz': "🛠️ Nimani tahrirlamoqchisiz?",
        'ru': "🛠️ Что хотите изменить?",
        'en': "🛠️ What would you like to edit?",
    },
    'edit_language': {
        'uz': "🌐 Tilni o‘zgartirish",
        'ru': "🌐 Сменить язык",
        'en': "🌐 Change language",
    },
    'edit_name': {
        'uz': "✏️ Ism/Familiya",
        'ru': "✏️ Имя/Фамилия",
        'en': "✏️ Name/Surname",
    },
    'edit_phone': {
        'uz': "📞 Telefon raqami",
        'ru': "📞 Номер телефона",
        'en': "📞 Phone number",
    },
    'enter_new_name': {
        'uz': "✍️ Yangi ism yoki to‘liq ism-familiyangizni yuboring:",
        'ru': "✍️ Отправьте новое имя или ФИО:",
        'en': "✍️ Send your new first name or full name:",
    },
    'enter_new_phone': {
        'uz': "📲 Yangi telefon raqamingizni yuboring:",
        'ru': "📲 Отправьте ваш новый номер телефона:",
        'en': "📲 Send your new phone number:",
    },
    'saved': {
        'uz': "✅ Saqlandi.",
        'ru': "✅ Сохранено.",
        'en': "✅ Saved.",
    },
    'settings_shortcut_hint': {
        'uz': "«/settings» — sozlamalarni ochish",
        'ru': "«/settings» — открыть настройки",
        'en': "Use “/settings” to open settings",
    },
}
