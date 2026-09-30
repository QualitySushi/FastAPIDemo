import asyncio
import json
import websockets
import numpy as np
from scipy.spatial import Voronoi

class MaritimeVoronoiEngine:
    def __init__(self, width: int = 800, height: int = 500, num_fallback: int = 20):
        self.width = width
        self.height = height
        self.vessels = {}
        
        # High-Density Bounding Box: The English Channel & Strait of Dover
        self.bbox = [[49.8, -1.5], [51.5, 2.0]]
        
        # Initialize persistent fallback positions & velocities for smooth movement when live feed is quiet
        self.fallback_positions = np.random.uniform(low=[50, 50], high=[width-50, height-50], size=(num_fallback, 2))
        angles = np.random.uniform(0, 2 * np.pi, num_fallback)
        speeds = np.random.uniform(0.5, 1.2, num_fallback)
        self.fallback_velocities = np.stack([speeds * np.cos(angles), speeds * np.sin(angles)], axis=-1)
        
        # Start background listener task for live data feed
        # asyncio.create_task(self.connect_live_ais_stream())

    async def connect_live_ais_stream(self):
        uri = "wss://stream.aisstream.io/v0/stream"
        api_key = "03d26961543398f8269d8f2dae19d65c48556dc3" 

        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    subscription = {
                        "APIKey": api_key,
                        "BoundingBoxes": [
                            [
                                [self.bbox[0][0], self.bbox[0][1]],
                                [self.bbox[1][0], self.bbox[1][1]]
                            ]
                        ],
                        "FilterMessageTypes": ["PositionReport"]
                    }
                    await websocket.send(json.dumps(subscription))
                    
                    async for message in websocket:
                        data = json.loads(message)
                        if data.get("MessageType") == "PositionReport":
                            msg = data.get("PositionReport", {})
                            meta = data.get("MetaData", {})
                            
                            mmsi = str(meta.get("MMSI"))
                            lat = msg.get("Latitude")
                            lon = msg.get("Longitude")
                            ship_name = meta.get("ShipName", f"Vessel {mmsi}").strip()
                            
                            if lat is not None and lon is not None:
                                x, y = self.project_latlon_to_canvas(lat, lon)
                                self.vessels[mmsi] = {
                                    "id": mmsi,
                                    "name": ship_name,
                                    "x": x,
                                    "y": y
                                }
            except Exception as e:
                print(f"[AIS Stream Error]: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    def project_latlon_to_canvas(self, lat: float, lon: float):
        lat_min, lon_min = self.bbox[0]
        lat_max, lon_max = self.bbox[1]
        
        nx = (lon - lon_min) / (lon_max - lon_min)
        ny = (lat - lat_min) / (lat_max - lat_min)
        
        x = np.clip(nx * (self.width - 100) + 50, 30, self.width - 30)
        y = np.clip((1.0 - ny) * (self.height - 100) + 50, 30, self.height - 30)
        
        return float(x), float(y)

    def compute_tessellation(self):
        active_vessels = list(self.vessels.values())
        is_live = len(active_vessels) >= 4
        
        if not is_live:
            self.fallback_positions += self.fallback_velocities
            
            for i in range(len(self.fallback_positions)):
                if self.fallback_positions[i, 0] < 30 or self.fallback_positions[i, 0] > self.width - 30:
                    self.fallback_velocities[i, 0] *= -1
                if self.fallback_positions[i, 1] < 30 or self.fallback_positions[i, 1] > self.height - 30:
                    self.fallback_velocities[i, 1] *= -1
                    
            self.fallback_positions[:, 0] = np.clip(self.fallback_positions[:, 0], 20, self.width - 20)
            self.fallback_positions[:, 1] = np.clip(self.fallback_positions[:, 1], 20, self.height - 20)
            
            points = self.fallback_positions
            point_ids = [f"fallback_{i}" for i in range(len(points))]
        else:
            points = np.array([[v["x"], v["y"]] for v in active_vessels])
            point_ids = [v["id"] for v in active_vessels]

        vor = Voronoi(points)

        polygons = []
        for point_idx, region_idx in enumerate(vor.point_region):
            region = vor.regions[region_idx]
            if region and -1 not in region:
                polygon = [vor.vertices[i].tolist() for i in region]
                
                poly_arr = np.array(polygon)
                area = 0.5 * np.abs(np.dot(poly_arr[:, 0], np.roll(poly_arr[:, 1], 1)) - 
                                   np.dot(poly_arr[:, 1], np.roll(poly_arr[:, 0], 1)))

                polygons.append({
                    "id": point_ids[point_idx],
                    "centroid": points[point_idx].tolist(),
                    "vertices": polygon,
                    "area": float(area)
                })

        return {
            "isLive": is_live,
            "vesselCount": len(points),
            "bbox": self.bbox,
            "polygons": polygons,
            "points": points.tolist()
        }