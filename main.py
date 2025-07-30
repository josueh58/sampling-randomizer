import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import random
from folium.plugins import Draw

st.set_page_config(page_title="Reservoir Sampling Randomizer", layout="wide")
st.title("🎣 Reservoir Sampling Site Randomizer")

# === Reservoir Definitions ===
RESERVOIRS = {
    "Steinaker Reservoir": {
        "lat_min": 40.515, "lat_max": 40.525,
        "lon_min": -109.575, "lon_max": -109.55
    },
    "Red Fleet Reservoir": {
        "lat_min": 40.618, "lat_max": 40.628,
        "lon_min": -109.475, "lon_max": -109.455
    }
}

# === User Sidebar Inputs ===
with st.sidebar:
    reservoir = st.selectbox("🗺️ Select Reservoir", list(RESERVOIRS.keys()))
    num_sites = st.slider("🔢 Number of Random Sites", 1, 20, 6)
    generate = st.button("🎲 Generate Sites")
    clear = st.button("🗑️ Clear All Sites")

bounds = RESERVOIRS[reservoir]

# === Session State Setup ===
if "points" not in st.session_state:
    st.session_state.points = []

# === Generate Random Sites ===
if generate:
    points = []
    for _ in range(num_sites):
        lat = round(random.uniform(bounds["lat_min"], bounds["lat_max"]), 6)
        lon = round(random.uniform(bounds["lon_min"], bounds["lon_max"]), 6)
        points.append((lat, lon))
    st.session_state.points = points

# === Clear Points ===
if clear:
    st.session_state.points = []

# === Map Center Calculation ===
center_lat = (bounds["lat_min"] + bounds["lat_max"]) / 2
center_lon = (bounds["lon_min"] + bounds["lon_max"]) / 2

# === Create Map ===
m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="Esri.WorldImagery")

# Add existing (randomized) points
for i, (lat, lon) in enumerate(st.session_state.points):
    folium.Marker([lat, lon], popup=f"Site {i + 1}", icon=folium.Icon(color="blue")).add_to(m)

# Add drawing tools to manually add/move points
Draw(export=True, draw_options={"polyline": False, "rectangle": False,
                                "polygon": False, "circle": False, "circlemarker": False}).add_to(m)

# === Display Map and Handle Edits ===
st.subheader("🗺️ Map View")
st_map_data = st_folium(m, key="map", height=600, width=1000)

# === Parse new points if drawn ===
if "all_drawings" in st_map_data and st_map_data["all_drawings"]:
    drawn_points = []
    for shape in st_map_data["all_drawings"]:
        if shape["geometry"]["type"] == "Point":
            coords = shape["geometry"]["coordinates"]
            drawn_points.append((round(coords[1], 6), round(coords[0], 6)))
    if drawn_points:
        st.session_state.points = drawn_points
        st.success("🟢 Sampling sites updated from drawn points!")

# === Show Updated Coordinates ===
if st.session_state.points:
    st.subheader("📍 Sample Site Coordinates")
    df = pd.DataFrame(st.session_state.points, columns=["Latitude", "Longitude"])
    st.dataframe(df)

    # Download CSV
    st.download_button(
        label="📥 Download as CSV",
        data=df.to_csv(index=False),
        file_name="sampling_sites.csv",
        mime="text/csv"
    )
else:
    st.info("Use 'Generate Sites' or draw points on the map to get started.")
