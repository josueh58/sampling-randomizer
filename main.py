import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Polygon, box, Point
import random
import pandas as pd
from shapely.ops import transform
import pyproj
import math

st.set_page_config(page_title="Reservoir Sampling Grid", layout="wide")
st.title("🎣 Reservoir Sampling Randomizer v2.9")

# === Reservoir centers
RESERVOIRS = {
    "Steinaker Reservoir": [40.525, -109.55],
    "Red Fleet Reservoir": [40.625, -109.465],
    "Big Sandwash Reservoir": [40.314, -110.058]
}

st.sidebar.subheader("📍 Reservoir Centering")
selected_res = st.sidebar.selectbox("Center Map On", list(RESERVOIRS.keys()))
center_latlon = RESERVOIRS[selected_res]

num_sites = st.sidebar.slider("🎯 Number of Random Sample Sites", 1, 50, 6)
generate = st.sidebar.button("⚙️ Generate Sites")

# === Session State
if "lake_polygon" not in st.session_state:
    st.session_state.lake_polygon = None
if "site_coords" not in st.session_state:
    st.session_state.site_coords = []
if "grid_size_m" not in st.session_state:
    st.session_state.grid_size_m = None
if "grid_size_deg" not in st.session_state:
    st.session_state.grid_size_deg = None

# === Draw polygon on map
m = folium.Map(location=center_latlon, zoom_start=15, tiles="Esri.WorldImagery")
Draw(export=True).add_to(m)
draw_data = st_folium(m, height=600, width=1000)

# === Main logic
if generate:
    drawings = draw_data.get("all_drawings", [])
    if not drawings:
        st.error("⚠️ Please draw a polygon first.")
    else:
        shape = drawings[0]
        if shape["geometry"]["type"] != "Polygon":
            st.error("⚠️ Only polygon shapes are accepted.")
        else:
            coords = shape["geometry"]["coordinates"][0]
            lake_poly = Polygon(coords)
            st.session_state.lake_polygon = lake_poly

            # Project polygon to UTM for area calculation
            project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32612", always_xy=True).transform
            lake_poly_utm = transform(project, lake_poly)
            area_m2 = lake_poly_utm.area
            area_acres = area_m2 * 0.000247105
            st.sidebar.markdown(f"📏 Lake Area: **{area_acres:.1f} acres**")

            # Apply AFS-based spacing
            if area_acres < 300:
                grid_size_m = 61
            elif area_acres <= 800:
                grid_size_m = 91
            else:
                grid_size_m = 122  # or 100 if you'd rather round down

            st.session_state.grid_size_m = grid_size_m
            st.sidebar.markdown(f"📐 Grid Cell Spacing: **{grid_size_m} meters**")

            # Convert meters to degrees
            meters_per_degree = 111000
            grid_size_deg = grid_size_m / meters_per_degree
            st.session_state.grid_size_deg = grid_size_deg

            # Create grid in degrees
            minx, miny, maxx, maxy = lake_poly.bounds
            grid_cells = []
            x = minx
            while x < maxx:
                y = miny
                while y < maxy:
                    cell = box(x, y, x + grid_size_deg, y + grid_size_deg)
                    if lake_poly.intersects(cell):
                        grid_cells.append(cell)
                    y += grid_size_deg
                x += grid_size_deg

            grid_gdf = gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:4326")

            if len(grid_gdf) == 0:
                st.error("❌ Grid generation failed — too small or invalid polygon.")
            else:
                selected_cells = grid_gdf.sample(min(num_sites, len(grid_gdf)))
                centroids = [(cell.centroid.y, cell.centroid.x) for cell in selected_cells.geometry]
                st.session_state.site_coords = centroids
                st.success("✅ Random sites generated!")

# === Display map with draggable sites
if st.session_state.lake_polygon and st.session_state.site_coords:
    final_map = folium.Map(location=[st.session_state.lake_polygon.centroid.y,
                                     st.session_state.lake_polygon.centroid.x],
                           zoom_start=15, tiles="Esri.WorldImagery")

    # Add lake polygon
    folium.GeoJson(st.session_state.lake_polygon, name="Lake Boundary").add_to(final_map)

    # Add grid (optional for visibility)
    gsize = st.session_state.grid_size_deg
    minx, miny, maxx, maxy = st.session_state.lake_polygon.bounds
    x = minx
    while x < maxx:
        y = miny
        while y < maxy:
            cell = box(x, y, x + gsize, y + gsize)
            if st.session_state.lake_polygon.intersects(cell):
                folium.GeoJson(cell, style_function=lambda x: {
                    "color": "gray", "weight": 1, "fillOpacity": 0
                }).add_to(final_map)
            y += gsize
        x += gsize

    # Add draggable markers
    for i, (lat, lon) in enumerate(st.session_state.site_coords):
        folium.Marker(
            location=[lat, lon],
            popup=f"Site {i + 1}",
            draggable=True,
            icon=folium.Icon(color="blue")
        ).add_to(final_map)

    st.subheader("🗺️ Adjust Site Locations")
    updated_data = st_folium(final_map, height=600, width=1000)

    # === Parse any updated marker locations
    updated_coords = []
    if updated_data.get("last_object_clicked") or updated_data.get("all_drawings"):
        for marker in updated_data.get("all_drawings", []):
            if marker["geometry"]["type"] == "Point":
                coords = marker["geometry"]["coordinates"]
                updated_coords.append((coords[1], coords[0]))  # lat, lon
        if updated_coords:
            st.session_state.site_coords = updated_coords
            st.success("🟢 Site locations updated from manual edits!")

    # === Download CSV
    df = pd.DataFrame(st.session_state.site_coords, columns=["Latitude", "Longitude"])
    st.subheader("📥 Download Coordinates")
    st.download_button("Download CSV", df.to_csv(index=False), "adjusted_sites.csv", "text/csv")


