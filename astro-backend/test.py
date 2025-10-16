from astroquery.jplhorizons import Horizons
from astropy.time import Time

def get_planet_ephem(name):
    # Horizons IDs for planets and Moon (geocentric)
    horizons_ids = {
        "Mercury": "199",
        "Venus": "299",
        "Mars": "499",
        "Jupiter": "599",
        "Saturn": "699",
        "Uranus": "799",
        "Neptune": "899",
        "Pluto": "999",
        "Moon": "301"
    }

    if name not in horizons_ids:
        print(f"{name} not in Horizons ID map")
        return

    try:
        obj = Horizons(id=horizons_ids[name], location='500', epochs=Time.now().jd)
        eph = obj.ephemerides()
        ra_deg = eph['RA'][0]
        dec_deg = eph['DEC'][0]
        print(f"{name}: RA = {ra_deg:.4f}°, Dec = {dec_deg:.4f}°")
    except Exception as e:
        print(f"Error querying {name}: {e}")

if __name__ == "__main__":
    objects = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn",
               "Uranus", "Neptune", "Pluto", "Moon"]
    for obj_name in objects:
        get_planet_ephem(obj_name)
