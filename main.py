import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import random

# Page setup
st.set_page_config(page_title="Reservoir Sampling Randomizer", layout="wide")
st.title("🎣 Reservoir Sampling Site Randomizer")

# Reservoir options with bounding boxes
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

# Sidebar user controls
with st.sidebar:
    reservoir = st.selectbox("🗺️ Select Reservoir", list(RESERVOIRS.keys()))
    num_sites = st.slider("🔢 Number of Sampling Sites", 1, 20, 5)
    generate = st.button("🎲 Generate Random Sites")

# Session state to persist results
if "points" not in st.session_state:
    st.session_state.points = []

# Generate sites on button click
if generate:
    bounds = RESERVOIRS[reservoir]
    points = []
    for _ in range(num_sites):
        lat = round(random.uniform(bounds["lat_min"], bounds["lat_max"]), 6)
        lon = round(random.uniform(bounds["lon_min"], bounds["lon_max"]), 6)
        points.append((lat, lon))
    st.session_state.points = points

# Display if we have points
if st.session_state.points:
    st.subheader("📍 Sampling Coordinates")
    df = pd.DataFrame(st.session_state.points, columns=["Latitude", "Longitude"])
    st.dataframe(df)

    # Create and display map
    center_lat = sum([p[0] for p in st.session_state.points]) / len(st.session_state.points)
    center_lon = sum([p[1] for p in st.session_state.points]) / len(st.session_state.points)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="Esri.WorldImagery")

    for idx, (lat, lon) in enumerate(st.session_state.points):
        folium.Marker([lat, lon], popup=f"Site {idx + 1}").add_to(m)

    st.subheader("🗺️ Map View")
    st_data = st_folium(m, width=1000, height=600)

    # Export button
    st.download_button(
        "📥 Download Coordinates as CSV",
        data=df.to_csv(index=False),
        file_name="sampling_sites.csv",
        mime="text/csv"
    )
else:
    st.info("Use the sidebar to generate sampling points.")
