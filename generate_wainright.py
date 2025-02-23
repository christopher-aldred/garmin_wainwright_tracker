#!/usr/bin/env python3

# Standard library imports
import datetime
import glob
import json
import logging
import math
import os
import time
from datetime import date

# Third-party imports
import numpy as np
import folium
from folium import plugins
import gpxpy
import requests
from garth.exc import GarthHTTPError
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
)
from dotenv import load_dotenv

# Local imports
import wainwright_list

# Global variables
all_achieved = set()
wainwright_tracks = []  # Stores tracks that pass near Wainwrights

# ---- DISTANCE CALCULATIONS ----

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Optimized version of haversine distance calculation."""
    # Pre-calculate radians once
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 12742000 * math.asin(math.sqrt(a))  # 2 * 6371000

# ---- GARMIN API FUNCTIONS ----

def display_json(api_call, output):
    """Format API output for better readability."""
    dashed = "-" * 20
    header = f"{dashed} {api_call} {dashed}"
    footer = "-" * len(header)
    print(header)
    if isinstance(output, (int, str, dict, list)):
        print(json.dumps(output, indent=4))
    else:
        print(output)
    print(footer)

def init_api(email, password):
    """Initialize Garmin API with credentials."""
    try:
        if not email or not password:
            raise Exception("Login credentials not set")
        garmin = Garmin(email=email, password=password, is_cn=False)
        garmin.login()
        return garmin
    except (
        FileNotFoundError,
        GarthHTTPError,
        GarminConnectAuthenticationError,
        requests.exceptions.HTTPError,
    ) as err:
        logger.error(err)
        return None

def get_gpx_data():
    """Download GPX data from Garmin Connect API."""
    today = date.today()
    previous_date = datetime.datetime.today() - datetime.timedelta(days=99999)

    activities1 = api.get_activities_by_date(previous_date.isoformat(), today.isoformat(), 'hiking')
    activities2 = api.get_activities_by_date(previous_date.isoformat(), today.isoformat(), 'walking')
    activities3 = api.get_activities_by_date(previous_date.isoformat(), today.isoformat(), 'running')
    all_activities = np.concatenate((activities1, activities2, activities3))

    for activity in all_activities:
        activity_start_time = datetime.datetime.strptime(
            activity["startTimeLocal"], "%Y-%m-%d %H:%M:%S"
        ).strftime("%d-%m-%Y")
        activity_id = activity["activityId"]
        activity_name = activity["activityName"]

        existing_files = glob.glob(f"{gpx_dir}/*_{activity_id}.gpx")

        if not existing_files:
            gpx_data = api.download_activity(
                activity_id, dl_fmt=api.ActivityDownloadFormat.GPX
            )
            output_file = f"{gpx_dir}/{str(activity_name)}_{str(activity_start_time)}_{str(activity_id)}.gpx"
            with open(output_file, "wb") as fb:
                fb.write(gpx_data)

# ---- WAINWRIGHT PROCESSING FUNCTIONS ----

def find_achieved_wainwrights_batch(points: np.ndarray, wainwright_array: np.ndarray) -> set:
    """Vectorized version of find_achieved_wainwrights using NumPy."""
    LEEWAY = 100  # meters
    achieved = set()
    
    # Convert points to numpy array if not already
    points = np.array(points)
    
    if len(points) == 0:
        return achieved

    # Vectorized calculations
    lat1 = points[:, 0][:, np.newaxis]
    lon1 = points[:, 1][:, np.newaxis]
    lat2 = wainwright_array[:, 0]
    lon2 = wainwright_array[:, 1]

    # Vectorized haversine calculation
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    lat1, lat2 = np.radians(lat1), np.radians(lat2)
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    distances = 12742000 * np.arcsin(np.sqrt(a))
    
    # Find minimum distance to each peak
    min_distances = np.min(distances, axis=0)
    
    # Get indices of peaks within leeway
    achieved_indices = np.where(min_distances <= LEEWAY)[0]
    
    # Convert indices back to peak names
    achieved.update(list(wainwright_list.wainwrights.keys())[i] for i in achieved_indices)
    
    return achieved

def process_gpx_files():
    """Process GPX files with optimizations."""
    track_count = 0
    
    # Convert Wainwright coordinates to numpy array once
    wainwright_array = np.array(list(wainwright_list.wainwrights.values()))
    
    # Pre-filter GPX files
    gpx_files = [f for f in os.listdir(gpx_dir) if f.lower().endswith('.gpx')]
    
    for filename in gpx_files:
        track_count += 1
        
        try:
            with open(gpx_dir + filename, 'r') as gpx_file:
                gpx = gpxpy.parse(gpx_file)
                
                # Process tracks
                for track in gpx.tracks:
                    # Collect all points from all segments at once
                    all_points = []
                    track_points = []
                    
                    for segment in track.segments:
                        segment_points = [(p.latitude, p.longitude) for p in segment.points]
                        all_points.extend(segment_points)
                        track_points.extend([[p.latitude, p.longitude] for p in segment.points])
                    
                    if all_points:  # Only process if we have points
                        achieved = find_achieved_wainwrights_batch(np.array(all_points), wainwright_array)
                        if achieved:
                            wainwright_tracks.append(track_points)
                            all_achieved.update(achieved)
                
                # Process routes
                for route in gpx.routes:
                    route_points = [(p.latitude, p.longitude) for p in route.points]
                    track_points = [[p.latitude, p.longitude] for p in route.points]
                    
                    if route_points:  # Only process if we have points
                        achieved = find_achieved_wainwrights_batch(np.array(route_points), wainwright_array)
                        if achieved:
                            wainwright_tracks.append(track_points)
                            all_achieved.update(achieved)
                            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    print(f"\nProcessed {track_count} GPX files.")
    percentage_complete = (len(all_achieved) / len(wainwright_list.wainwrights)) * 100
    print(f"\nTotal unique Wainwrights achieved: {len(all_achieved)} out of {len(wainwright_list.wainwrights)} ({percentage_complete:.1f}%)")

# ---- MAP GENERATION FUNCTIONS ----

def generate_html():
    """Generate detailed HTML map with tracks and markers."""
    save_path = 'docs/index.html'

    m = folium.Map(
        location=[54.531822, -2.963408], 
        zoom_start=9.5, 
        zoom_control=False,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles &copy; Esri &mdash; Esri'
    )

    colors = ['darkblue', 'darkgreen', 'purple', 'darkred']
    
    for i, track in enumerate(wainwright_tracks):
        color = colors[i % len(colors)]
        folium.PolyLine(
            locations=track,
            weight=2,
            color=color,
            opacity=0.8,
            dash_array='4',
        ).add_to(m)

    for name, coords in wainwright_list.wainwrights.items():
        if name not in all_achieved:
            folium.RegularPolygonMarker(
                location=[coords[0], coords[1]],
                number_of_sides=3,
                radius=8,
                popup=name,
                color='rgba(255, 0, 0, 0.4)',
                fill=True,
                fill_color='red',
                fill_opacity=0.2,
                rotation=30,
                zIndex=1
            ).add_to(m)

    for name, coords in wainwright_list.wainwrights.items():
        if name in all_achieved:
            folium.RegularPolygonMarker(
                location=[coords[0], coords[1]],
                number_of_sides=3,
                radius=10,
                popup=name,
                color='green',
                fill=True,
                fill_color='#90EE90',
                rotation=30,
                fill_opacity=0.6,
                zIndex=2
            ).add_to(m)

    legend_html = '''
        <style>
            @media screen and (max-width: 768px) {
                .legend-box {
                    display: none;
                }
            }
        </style>
        <div class="legend-box"style="position: fixed;
            bottom: 50px; right: 50px; width: 150px; height: 110px;
            border:2px solid grey; z-index:9999; background-color:white;
            opacity:0.8;
            ">
            
            <div class="legend-container">
                &nbsp; Legend <br>
                &nbsp; <span style="color:green">▲</span> Completed<br>
                &nbsp; <span style="color:red">▲</span> Not completed<br>
                &nbsp; <span style="color:purple">―</span> Tracks with peaks<br>
            </div>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))

    completed_count = len(all_achieved)
    total_count = len(wainwright_list.wainwrights)
    stats_html = f'''
    <div style="position: fixed;
        top: 50px; right: 50px; width: 150px; height: 90px;
        border:2px solid grey; z-index:9999; background-color:white;
        opacity:0.8;
        ">
        &nbsp; Progress <br>
        &nbsp; Completed: {completed_count}<br>
        &nbsp; Remaining: {total_count - completed_count}<br>
        &nbsp; Total: {total_count}<br>
        </div>
    '''
    m.get_root().html.add_child(folium.Element(stats_html))
    m.save(save_path)

# ---- MAIN EXECUTION ----

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Create GPX directory
    gpx_dir = './GPX_files/'
    if not os.path.exists(gpx_dir):
        os.makedirs(gpx_dir)
    
    # Handle Garmin Connect integration
    if os.getenv("GARMIN_EMAIL") and os.getenv("GARMIN_PASSWORD"):
        api = init_api(email=os.getenv("GARMIN_EMAIL"), password=os.getenv("GARMIN_PASSWORD"))
        display_json("api.get_full_name()", api.get_full_name())
        print("Downloading GPX data from Garmin Connect...")
        get_gpx_data()
    else:
        print("Garmin Connect integration disabled - no credentials provided")

    # Process files and generate outputs
    print("Processing GPX files...")
    process_gpx_files()
    
    print("Generating HTML map...")
    generate_html()