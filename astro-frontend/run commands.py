npm run dev
C:\Users\olsen>ngrok start --all
C:\Users\olsen\Documents\astro-backend>uvicorn main:app --host 0.0.0.0 --port 8000

https://eb59902b548c.ngrok-free.app/target/M57


# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from astroquery.simbad import Simbad
from astroquery.jplhorizons import Horizons   # NEW
from astropy.coordinates import SkyCoord
import astropy.units as u
from fastapi.responses import JSONResponse
import json
import concurrent.futures
import asyncio
import os
from datetime import datetime

# SIMBAD setup
Simbad.add_votable_fields("ra", "dec")

# Thread pool for blocking operations
executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

# Cache for target results
TARGET_CACHE = {}

# Base directory for absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(BASE_DIR, "catalog.json")

# List of solar system objects we want to support
SOLAR_SYSTEM_OBJECTS = [
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",   # optional
    "Moon"
]

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Async-safe catalog fetch
@app.get("/catalog")
async def get_catalog():
    loop = asyncio.get_running_loop()

    def read_catalog():
        with open(CATALOG_PATH, "r") as f:
            return json.load(f)

    try:
        catalog_json = await loop.run_in_executor(executor, read_catalog)
        catalog_list = list(catalog_json["data"].values())

        # Add solar system objects to the catalog
        for obj in SOLAR_SYSTEM_OBJECTS:
            catalog_list.append({"name": obj})

        return JSONResponse(content=catalog_list)
    except Exception as e:
        print("Catalog load error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)


# Async-safe SIMBAD query
async def query_simbad_async(name: str):
    loop = asyncio.get_running_loop()

    def query():
        return Simbad.query_object(name)

    result = await loop.run_in_executor(executor, query)
    return result


# Async-safe JPL Horizons query
async def query_horizons_async(name: str):
    loop = asyncio.get_running_loop()

    def query():
        # Use JPL Horizons ephemeris query
        obj = Horizons(id=name, location="500", epochs=datetime.utcnow().strftime("%Y-%m-%d"))
        eph = obj.ephemerides()
        return eph

    eph = await loop.run_in_executor(executor, query)
    return eph


@app.get("/target/{name}")
async def get_target(name: str):
    # Return cached result if available
    if name in TARGET_CACHE:
        return TARGET_CACHE[name]

    # Check if name is solar system object
    if name in SOLAR_SYSTEM_OBJECTS:
        eph = await query_horizons_async(name)

        ra_deg = float(eph["RA"][0])   # deg
        dec_deg = float(eph["DEC"][0])

        coord = SkyCoord(ra=ra_deg*u.deg, dec=dec_deg*u.deg, frame="icrs")

        data = {
            "name": name,
            "ra": coord.ra.to_string(unit=u.hour, sep=":"),
            "ra_deg": ra_deg,
            "dec": coord.dec.to_string(unit=u.deg, sep=":"),
            "dec_deg": dec_deg,
        }

        TARGET_CACHE[name] = data
        return data

    # Otherwise query SIMBAD
    result = await query_simbad_async(name)
    if result is None:
        return {"error": "Object not found"}

    ra_deg = float(result["ra"][0])
    dec_deg = float(result["dec"][0])

    coord = SkyCoord(ra=ra_deg*u.deg, dec=dec_deg*u.deg, frame="icrs")

    data = {
        "name": name,
        "ra": coord.ra.to_string(unit=u.hour, sep=":"),
        "ra_deg": ra_deg,
        "dec": coord.dec.to_string(unit=u.deg, sep=":"),
        "dec_deg": dec_deg,
    }

    TARGET_CACHE[name] = data
    return data








# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from astroquery.simbad import Simbad
from astroquery.jplhorizons import Horizons
from astropy.coordinates import SkyCoord
import astropy.units as u
from fastapi.responses import JSONResponse
import json
import concurrent.futures
import asyncio
import os
from datetime import datetime

# SIMBAD setup
Simbad.add_votable_fields("ra", "dec")

# Thread pool for blocking operations
executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

# Cache for target results
TARGET_CACHE = {}

# Base directory for absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_PATH = os.path.join(BASE_DIR, "catalog.json")

# Solar system objects set (must match names in catalog.json)
SOLAR_SYSTEM_SET = {
    "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
    "Uranus", "Neptune", "Pluto", "Moon"
}

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Catalog endpoint
# -----------------------------
@app.get("/catalog")
async def get_catalog():
    loop = asyncio.get_running_loop()

    def read_catalog():
        with open(CATALOG_PATH, "r") as f:
            return json.load(f)

    try:
        catalog_json = await loop.run_in_executor(executor, read_catalog)
        catalog_list = list(catalog_json.values())  # keep values only
        return JSONResponse(content=catalog_list)
    except Exception as e:
        print("Catalog load error:", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)


# -----------------------------
# Query helpers
# -----------------------------
async def query_simbad_async(name: str):
    loop = asyncio.get_running_loop()

    def query():
        return Simbad.query_object(name)

    return await loop.run_in_executor(executor, query)


async def query_horizons_async(name: str):
    loop = asyncio.get_running_loop()

    def query():
        # Horizons ephemeris query at current UTC
        obj = Horizons(id=name, location="500", epochs=datetime.utcnow().strftime("%Y-%m-%d"))
        return obj.ephemerides()

    return await loop.run_in_executor(executor, query)


# -----------------------------
# Target lookup endpoint
# -----------------------------
@app.get("/target/{name}")
async def get_target(name: str):
    # Check cache first
    if name in TARGET_CACHE:
        return TARGET_CACHE[name]

    # Check if the object is in the catalog (for planets/Moon)
    with open(CATALOG_PATH, "r") as f:
        catalog = json.load(f)["data"]
    obj = catalog.get(name)
    if obj and obj.get("type") in ["Planet", "Moon"]:
        data = {
            "name": obj["name"],
            "ra": "0:00:00",        # placeholder
            "ra_deg": 0.0,          # placeholder
            "dec": "0:00:00",       # placeholder
            "dec_deg": 0.0,         # placeholder
        }
        TARGET_CACHE[name] = data
        return data

    # Otherwise, query SIMBAD
    result = await query_simbad_async(name)
    if result is None:
        return {"error": "Object not found"}

    ra_deg = float(result["ra"][0])
    dec_deg = float(result["dec"][0])
    coord = SkyCoord(ra=ra_deg*u.deg, dec=dec_deg*u.deg, frame="icrs")

    data = {
        "name": name,
        "ra": coord.ra.to_string(unit=u.hour, sep=":"),
        "ra_deg": ra_deg,
        "dec": coord.dec.to_string(unit=u.deg, sep=":"),
        "dec_deg": dec_deg,
    }

    TARGET_CACHE[name] = data
    return data


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