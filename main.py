import streamlit as st
import folium
from streamlit_folium import st_folium
import random
import pandas as pd

st.set_page_config(page_title="Reservoir Sampling Randomizer", layout="wide")
st.title("🎣 Reservoir Sampling Site Randomizer")

# === SETTINGS ===
# Hardcoded bounding boxes for demonstration
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

# Sidebar inputs
with st.sidebar:
    reservoir = st.selectbox("Select Reservoir", list(RESERVOIRS.keys()))
    num_sites = st.slider("Number of Random Sample Sites", min_value=1, max_value=20, value=5)
    generate = st.button("🎲 Generate Sites")

# Get bounds for selected reservoir
bounds = RESERVOIRS[reservoir]
random_points = []

if generate:
    # Random points within bounding box
    for _ in range(num_sites):
        lat = round(random.uniform(bounds["lat_min"], bounds["lat_max"]), 6)
        lon = round(random.uniform(bounds["lon_min"], bounds["lon_max"]), 6)
        random_points.append((lat, lon))

    df_coords = pd.DataFrame(random_points, columns=["Latitude", "Longitude"])
    st.subheader("📍 Sample Site Coordinates")
    st.dataframe(df_coords)

    # Create map
    center_lat = (bounds["lat_min"] + bounds["lat_max"]) / 2
    center_lon = (bounds["lon_min"] + bounds["lon_max"]) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="Esri.WorldImagery")

    # Add each point as a marker
    for i, (lat, lon) in enumerate(random_points):
        folium.Marker([lat, lon], tooltip=f"Site {i+1}").add_to(m)

    # Render interactive map
    st.subheader("🗺️ Map View")
    st_folium(m, width=1000, height=600)

    # Download button
    st.download_button(
        label="📥 Download Coordinates as CSV",
        data=df_coords.to_csv(index=False),
        file_name="sampling_sites.csv",
        mime="text/csv"
    )
else:
    st.info("Select options and click 'Generate Sites' to begin.")
