import requests, backoff, logging
from typing import Optional, List, Dict, Any, Tuple
from config import GOOGLE_MAPS_API_KEY, RADIUS_METERS, MAX_RESULTS

logger = logging.getLogger(__name__)

BASE = "https://places.googleapis.com/v1"

# Request only **leaf fields** (New Places API requirement)
FIELD_MASK_NEARBY = ",".join([
    "places.name",
    "places.displayName.text",
    "places.formattedAddress",
    "places.location",  # allowed as an object
    "places.primaryType",
    "places.rating",
    "places.userRatingCount",
    "places.currentOpeningHours.openNow",
    "places.currentOpeningHours.weekdayDescriptions",  # human lines like "Monday: 9AM–5PM"
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.websiteUri",
    "places.googleMapsUri",
    "places.photos.name",
])

FIELD_MASK_TEXT = "places.location"

COMMON_HEADERS = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
}

# Updated categories mapping (canonical English keys)
CATEGORY_TYPE_MAP = {
    "Restaurant": ["restaurant", "cafe", "bakery"],
    "Hotel": ["lodging"],
    "Park": ["park"],
    "Historic Places": ["tourist_attraction", "museum", "art_gallery"],
}

def _type_filter_for_category(category: str) -> Optional[List[str]]:
    return CATEGORY_TYPE_MAP.get(category) or None

def _headers_with_fieldmask(mask: str) -> Dict[str, str]:
    h = COMMON_HEADERS.copy()
    h["X-Goog-FieldMask"] = mask
    return h

def _raise_with_details(resp: requests.Response):
    try:
        details = resp.json()
    except Exception:
        details = resp.text
    logger.error("Google Places error %s: %s", resp.status_code, details)
    resp.raise_for_status()

@backoff.on_exception(backoff.expo, (requests.exceptions.RequestException,), max_tries=3)
def search_nearby(lat: float, lng: float, category: str) -> List[Dict[str, Any]]:
    body: Dict[str, Any] = {
        "maxResultCount": MAX_RESULTS,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": RADIUS_METERS
            }
        }
    }
    types = _type_filter_for_category(category)
    if types:
        body["includedTypes"] = types

    headers = _headers_with_fieldmask(FIELD_MASK_NEARBY)
    resp = requests.post(f"{BASE}/places:searchNearby", headers=headers, json=body, timeout=20)
    if not resp.ok:
        _raise_with_details(resp)

    data = resp.json()
    return data.get("places", [])

@backoff.on_exception(backoff.expo, (requests.exceptions.RequestException,), max_tries=3)
def search_text(query: str) -> Optional[Tuple[float, float]]:
    body = {"textQuery": query, "maxResultCount": 1}
    headers = _headers_with_fieldmask(FIELD_MASK_TEXT)
    resp = requests.post(f"{BASE}/places:searchText", headers=headers, json=body, timeout=20)
    if not resp.ok:
        _raise_with_details(resp)

    data = resp.json()
    places = data.get("places", [])
    if not places:
        return None
    loc = places[0].get("location", {})
    return loc.get("latitude"), loc.get("longitude")

@backoff.on_exception(backoff.expo, (requests.exceptions.RequestException,), max_tries=3)
def get_photo_url(photo_name: str, max_height: int = 800) -> Optional[str]:
    url = f"{BASE}/{photo_name}/media?maxHeightPx={max_height}&key={GOOGLE_MAPS_API_KEY}"
    resp = requests.get(url, allow_redirects=False, timeout=20)
    if resp.status_code in (302, 303) and 'Location' in resp.headers:
        return resp.headers['Location']
    if resp.ok:
        return url
    logger.warning("Photo fetch failed: %s %s", resp.status_code, resp.text)
    return None

@backoff.on_exception(backoff.expo, (requests.exceptions.RequestException,), max_tries=3)
def reverse_geocode(lat: float, lng: float, language: str = "en") -> Optional[str]:
    """Return a human-readable formatted address using Google Geocoding API.
    Preference order: neighborhood/sublocality > route + street_number > locality > plus_code > first result.
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "latlng": f"{lat},{lng}",
        "key": GOOGLE_MAPS_API_KEY,
        "language": language,
    }
    resp = requests.get(url, params=params, timeout=20)
    if not resp.ok:
        logger.error("Geocoding API error %s: %s", resp.status_code, resp.text)
        return None
    data = resp.json()
    results = data.get("results") or []
    if not results:
        return None

    def _has_type(r: Dict[str, Any], types: List[str]) -> bool:
        ts = r.get("types") or []
        return any(t in ts for t in types)

    # Try to pick a result that represents a human-readable area/road
    preferred_orders = [
        ["sublocality", "sublocality_level_1", "neighborhood"],
        ["route"],
        ["locality", "administrative_area_level_2"],
    ]
    for wanted in preferred_orders:
        for r in results:
            if _has_type(r, wanted):
                return r.get("formatted_address")

    # If none matched, try plus_code
    plus = data.get("plus_code", {}) or {}
    plus_global = plus.get("global_code")
    plus_compound = plus.get("compound_code")
    if plus_compound:
        return plus_compound
    if plus_global:
        return plus_global

    # Fallback to the first formatted address
    return results[0].get("formatted_address")
