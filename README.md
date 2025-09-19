# Telegram Tourist Bot (Google Places API — v1 “New”)
A multilingual Telegram bot that lets users search nearby places (2 km) by category using **Google Places API (New)**. It collects the user's language, name, and phone, saves them in SQLite, and shows rich place cards with open/closed info, photo, and navigation buttons for **Google Maps** and **Yandex Maps**. Each screen provides a **Back** button.

## Features
- Languages: **Uzbek**, **Russian**, **English**
- Collects **name**, **surname**, **contact (phone)** via Telegram contact button or manual text
- Input: user can **send their current location** or **type a place/address name**
- **6 categories**: Food & Dining; Attractions & Entertainment; Nature & Outdoors; Culture & Religion; Shopping & Lifestyle; Accommodation
- Google Places (New) **Nearby Search** within **2 km**
- Beautiful cards with **photo, status (open/closed), rating, address**, and inline buttons:
  - **Open in Google Maps**
  - **Open in Yandex Maps**
  - **Back**
- All user profiles saved in **SQLite**

## Quick Start
1. **Python 3.10+** recommended.
2. `pip install -r requirements.txt`
3. Set environment in `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_TOKEN
   GOOGLE_MAPS_API_KEY=YOUR_GOOGLE_PLACES_API_KEY
   ```
4. Run:
   ```bash
   python app.py
   ```

## Notes on Google Places API (New)
- Nearby search endpoint: `POST https://places.googleapis.com/v1/places:searchNearby`
- Required headers:
  - `X-Goog-Api-Key: <YOUR_KEY>`
  - `X-Goog-FieldMask: places.displayName,places.formattedAddress,places.location,places.currentOpeningHours,places.rating,places.userRatingCount,places.name,places.primaryType,places.photos`
- Photo media endpoint (first photo example):
  - `GET https://places.googleapis.com/v1/{photoName}/media?maxHeightPx=800&key=<YOUR_KEY>`
- Geocoding: we use Places **Text Search** when user types an address/place:
  - `POST https://places.googleapis.com/v1/places:searchText`

## Project Structure
```
tg_tourist_bot/
├─ app.py
├─ config.py
├─ db.py
├─ requirements.txt
├─ .env  # create this
├─ bot/
│  ├─ keyboards.py
│  ├─ handlers.py
│  └─ locale.py
└─ services/
   ├─ google_places.py
   └─ utils.py
```

## Database
- SQLite file `bot.db`:
  - `users(id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, language TEXT, first_name TEXT, last_name TEXT, phone TEXT)`

## Security
- Keep API keys in `.env` and **never commit** them.
- Consider usage quotas and billing for Google APIs.

## License
MIT
