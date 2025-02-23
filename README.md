# Wainwright Peak Tracker ⛰️

This repo contains Python scripts that track progress of  Wainwright peak completion in the Lake District and generates an interactive map. The code integrates with Garmin Connect to pull GPS data from activities and generates interactive maps showing completed and remaining peaks.

![map screenshot](screenshot.png)

## Features

- Pulls activity data (hiking, walking, running) from Garmin Connect API
- Processes GPX files to identify visited Wainwright peaks
- Generates two interactive HTML maps:
  - `index.html`: Detailed map showing completed peaks, remaining peaks, and GPS tracks
  - `map.jpg`: Simplified saturated map showing just completed and remaining peaks with QR code (Designed for E-ink screen)

## Deployment

To set up automatic deployment:

1. **Configure GitHub Secrets (optional)**

   - Go to your repository's Settings > Secrets and Variables > Actions
   - Add two new secrets:
     - `GARMIN_EMAIL`: Your Garmin Connect email
     - `GARMIN_PASSWORD`: Your Garmin Connect password

2. **Enable GitHub Actions Write Permissions**

   - Go to Settings > Actions > General
   - Under "Workflow permissions", select "Read and write permissions"
   - Click "Save"

3. **Run Initial Workflow**

   - Go to Actions > Midnight run
   - Click "Run workflow"
   - Wait for the workflow to complete and generate the initial HTML files

4. **Set up GitHub Pages**
   - Go to Settings > Pages
   - Under "Build and deployment", select:
     - Source: "Deploy from a branch"
     - Branch: "main" and "/docs"
   - Click "Save"

The maps will now automatically update and deploy to GitHub Pages whenever new activities are synced with Garmin Connect. (Refeshes 3am daily)

You can visit the site at: `https://<your-github-username>.github.io/<your-repository-name>`.

## Adding External GPX Files

If you have GPS tracks or routes that aren't from Garmin Connect, you can still include them:

1. Create a directory called `GPX_files` in the root of the project (if it doesn't exist)
2. Copy your .gpx files into this directory
3. The script will automatically process these files along with any Garmin Connect activities

This is useful for:

- Activities recorded with other devices/apps
- Historical hikes before using Garmin
- Routes from other hikers
- Manually created GPS tracks

Note: The GPX files must be valid GPS data in standard GPX format. Most GPS devices and hiking apps can export in this format.

## Files

- `generate_html.py`: Main Python script that generates the maps
- `my_vars.py`: Contains coordinates for Wainwright peaks
- `index.html`: Generated detailed map
- `basic.html`: Generated simplified map
- `.env`: Configuration file for Garmin Connect credentials (not tracked in git)

## How it works

1. The script connects to Garmin Connect API to download GPS data from activities
2. GPX files are processed to identify which Wainwright peaks have been visited
3. Interactive maps are generated using Folium showing:
   - Green triangles for completed peaks
   - Red triangles for remaining peaks
   - GPS tracks from activities (in detailed map)
   - Progress statistics
   - QR code (in basic map)

## Requirements

- Python 3.x
- Required packages: folium, gpxpy, garminconnect, dotenv, and others (see imports)
- Garmin Connect account credentials in `.env` file
