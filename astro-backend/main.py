# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from astroquery.simbad import Simbad
from astroquery.jplhorizons import Horizons
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from astropy.time import Time
import astropy.units as u
from fastapi.responses import JSONResponse
from datetime import timedelta
from typing import Optional
import json
import concurrent.futures
import asyncio
import numpy as np
import os

# --- SIMBAD setup ---
Simbad.add_votable_fields("ra(d)", "dec(d)")

# Thread pool for blocking operations
executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

# Cache for target results
TARGET_CACHE = {}

# Base directory for absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(BASE_DIR, "catalog.json")

app = FastAPI()

# --- CORS middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins, adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Planet/Moon Horizons IDs ---
HORIZONS_IDS = {
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

# --- Catalog endpoint ---
@app.get("/catalog")
async def get_catalog():
    loop = asyncio.get_running_loop()

    def read_catalog():
        with open(CATALOG_PATH, "r") as f:
            return json.load(f)  # now returns a list

    try:
        catalog_list = await loop.run_in_executor(executor, read_catalog)
        return JSONResponse(content=catalog_list)
    except Exception as e:
        print("Catalog load error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

# --- Async-safe SIMBAD query ---
async def query_simbad_async(name: str):
    loop = asyncio.get_running_loop()

    def query():
        return Simbad.query_object(name)

    return await loop.run_in_executor(executor, query)

# --- Async-safe Horizons query ---
async def query_horizons_async(name: str):
    loop = asyncio.get_running_loop()

    def query():
        obj = Horizons(id=HORIZONS_IDS[name], location="500", epochs=Time.now().jd)
        eph = obj.ephemerides()
        if len(eph) == 0:
            raise ValueError(f"Horizons returned no data for {name}")
        ra_deg = float(eph["RA"][0])
        dec_deg = float(eph["DEC"][0])
        return ra_deg, dec_deg

    return await loop.run_in_executor(executor, query)

# --- Observability helper with timezone-aware local time ---
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
import datetime

tf = TimezoneFinder()

def get_observability(coord, lat, lon, obstime):
    location = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=0 * u.m)

    # Sample 24 hours starting from obstime
    delta_hours = np.linspace(0, 24, 1400) * u.hour
    times = obstime + delta_hours

    altaz = coord.transform_to(AltAz(obstime=times, location=location))
    altitudes = altaz.alt

    # Max altitude and its time
    max_idx = np.argmax(altitudes)
    max_altitude = float(altitudes[max_idx].deg)
    transit_time_utc = times[max_idx].datetime  # UTC datetime

    # Determine timezone from lat/lon
    tz_str = tf.timezone_at(lat=lat, lng=lon)
    if tz_str is None:
        tz_str = "UTC"  # fallback
    local_tz = ZoneInfo(tz_str)

    transit_time_local = transit_time_utc.replace(tzinfo=datetime.timezone.utc).astimezone(local_tz)

    return {
        "max_altitude_deg": max_altitude,
        "transit_time_utc": transit_time_utc.isoformat(),
        "transit_time_local": transit_time_local.isoformat(),
        "timezone": tz_str,
    }

# --- Target endpoint ---
@app.get("/target/{name}")
async def get_target(
    name: str,
    lat: float = Query(..., description="Observer latitude in degrees"),
    lon: float = Query(..., description="Observer longitude in degrees"),
    time: Optional[str] = Query(None, description="ISO UTC datetime (optional)")
):
    try:
        obstime = Time.now() if time is None else Time(time)

        if name in HORIZONS_IDS:
            # Planets/Moon -> Horizons gives apparent-of-date coords
            ra_deg, dec_deg = await query_horizons_async(name)
            coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
        else:
            # Stars/DSOs from SIMBAD -> J2000 ICRS
            result = await query_simbad_async(name)
            if result is None:
                return {"error": "Object not found"}
            ra_deg = float(result["ra"][0])
            dec_deg = float(result["dec"][0])

            coord_icrs = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")

            # Precess to observation epoch (true equator and equinox of date)
            coord = coord_icrs.transform_to(
                SkyCoord(ra=coord_icrs.ra, dec=coord_icrs.dec,
                         frame="fk5", equinox=obstime)
            )

        # Observability
        observability = get_observability(coord, lat, lon, obstime)

        data = {
            "name": name,
            "ra": coord.ra.to_string(unit=u.hour, sep=":"),
            "ra_deg": coord.ra.deg,
            "dec": coord.dec.to_string(unit=u.deg, sep=":"),
            "dec_deg": coord.dec.deg,
            **observability
        }

        return data

    except Exception as e:
        return {"error": str(e)}