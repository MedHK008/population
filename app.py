# pip install fastapi uvicorn pymongo shapely pyproj
# uvicorn app:app --reload 
# api :
# GET http://127.0.0.1:8000/zones
# POST http://127.0.0.1:8000/zones


from fastapi import FastAPI, HTTPException
import uvicorn
from pymongo import MongoClient
from shapely.geometry import Polygon
from pyproj import Transformer
from pydantic import BaseModel
from typing import List

app = FastAPI()

#database
client = MongoClient("mongodb://localhost:27017/")
db = client.geofencingDB
zones_collection = db.zones

#Mohammédia
city_population = 220455
city_area_km2 = 33.76
city_density = city_population / city_area_km2

transformer = Transformer.from_crs("EPSG:4326", "EPSG:32630", always_xy=True)


@app.get("/zones")
def get_zones():
    residential_zones = zones_collection.find({"tags.landuse": "residential"})
    zones_response = []
    for zone in residential_zones:
        geometry = zone["geometry"]
        transformed_coords = [transformer.transform(coord["lon"], coord["lat"]) for coord in geometry]
        polygon = Polygon(transformed_coords)
        area_km2 = polygon.area / 1e6
        zone["tags"]["area_km2"] = area_km2
        zone_population = city_density * area_km2
        zones_response.append({
            "zoneId": zone["zoneId"],
            "type": zone["tags"]["landuse"],
            "area_km2": round(area_km2, 6),
            "population": round(zone_population, 2)
        })

    # Prepare API response
    api_response = {
        "city_density": round(city_density, 2),
        "zones": zones_response
    }

    return api_response


class ZoneRequest(BaseModel):
    zone_ids: List[str]

# REQUEST BODY
# {
#     "zone_ids": [
#         "zoneId1",
#         "zoneId2",
#         "zoneId3"
#     ]
# }
@app.post("/zones")
def get_zone_details(request: ZoneRequest):
    zones = zones_collection.find({"zoneId": {"$in": request.zone_ids}})
    
    if not zones:
        raise HTTPException(status_code=404, detail="Zones not found")

    zones_response = []
    for zone in zones:
        geometry = zone["geometry"]
        transformed_coords = [transformer.transform(coord["lon"], coord["lat"]) for coord in geometry]
        polygon = Polygon(transformed_coords)
        area_km2 = polygon.area / 1e6
        zone_population = city_density * area_km2

        zones_response.append({
            "zoneId": zone["zoneId"],
            "area_km2": round(area_km2, 6),
            "population": round(zone_population, 2)
        })

    return {"zones": zones_response}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)