import numpy as np
import requests
from skyfield.api import EarthSatellite, Loader

load = Loader('astro_data')
ts = load.timescale()

_cached_satellites = []

def fetch_satellite_constellation():
    """Fetches a multi-satellite TLE list from CelesTrak stations group."""
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            satellites_data = []
            for i in range(0, len(lines) - 2, 3):
                name = lines[i].strip()
                line1 = lines[i+1].strip()
                line2 = lines[i+2].strip()
                satellites_data.append((name, line1, line2))
            return satellites_data
    except Exception as e:
        print(f"Error fetching TLEs: {e}")
    return []

def initialize_satellites():
    """Initializes and caches satellite objects on startup with robust offline fallbacks."""
    global _cached_satellites
    raw_sats = []
    
    try:
        raw_sats = fetch_satellite_constellation()
    except Exception as e:
        print(f"Group fetch failed: {e}")
    
    if not raw_sats:
        url = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                lines = res.text.strip().split('\n')
                if len(lines) >= 3:
                    raw_sats = [(lines[0].strip(), lines[1].strip(), lines[2].strip())]
        except Exception:
            print("Warning: Network unreachable. Activating local offline fallback TLE data.")

    if not raw_sats:
        raw_sats = [
            (
                "ISS (ZARYA)",
                "1 25544U 98067A   26085.51445705  .00016717  00000-0  30583-3 0  9999",
                "2 25544  51.6415 147.2885 0004971 184.5518 316.5917 15.50186178443597"
            ),
            (
                "HUBBLE SPACE TELESCOPE",
                "1 20580U 90037B   26084.92134259  .00001234  00000-0  56789-4 0  9993",
                "2 20580  28.4698 120.4512 0002341  45.1234 315.1234 15.09123456345678"
            )
        ]

    _cached_satellites = []
    for idx, (name, line1, line2) in enumerate(raw_sats[:50]):
        try:
            sat = EarthSatellite(line1, line2, name, ts)
            _cached_satellites.append({"id": f"sat-{idx}", "name": name, "sat": sat})
        except Exception as e:
            print(f"Failed to parse TLE for {name}: {e}")
            continue
            
    print(f"Successfully initialized {len(_cached_satellites)} satellites for tracking.")

def get_satellite_constellation_positions():
    """Calculates current 3D Cartesian coordinates for cached satellites using advancing time."""
    if not _cached_satellites:
        initialize_satellites()
        if not _cached_satellites:
            return []

    t = ts.now()
    results = []

    for item in _cached_satellites:
        try:
            satellite = item["sat"]
            geocentric = satellite.at(t)
            pos_km = np.array(geocentric.position.km)
            
            sat_obj = {
                "id": item["id"],
                "name": item["name"],
                "x": float(pos_km[0]),
                "y": float(pos_km[1]),
                "z": float(pos_km[2]),
                "time": t.utc_iso()
            }
            results.append(sat_obj)
        except Exception:
            continue

    return results