from typing import Tuple
from math import radians, cos, sin, asin, sqrt

def clamp_latlng(lat: float, lng: float) -> Tuple[float, float]:
    return max(-90, min(90, lat)), max(-180, min(180, lng))

def haversine_km(lat1, lon1, lat2, lon2):
    # For optional local filtering/sorting if needed
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c
