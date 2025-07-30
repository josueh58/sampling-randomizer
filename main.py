import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Polygon, box
import random
import pandas as pd

st.set_page_config(page_title="Reservoir Sampling Grid", layout="wide")
st.title("🎣 Reservoir Sampling Randomizer v2.5")

# === Map Centers for known reservoirs ===
RESERVOIRS = {
    "Steinaker Reservoir": [40.525, -109.55],
    "Red Fleet Reservoir": [40.625, -109.465],
    "Big Sandwash Reservoir": [40.314, -110.058]
}

# === Sidebar Inputs ===
st.sidebar.subheader("📍 Reservoir + Sampling Settings")
selected_res = st.sidebar.selectbox("Select Reservoir to Center Map", list(RESERVOIRS.keys()))
center_latlon = RESERVOIRS[selected_res]

grid_size = st.sidebar.number_input("Grid Cell Size (degrees ~0.001 = ~110m)", value=0.001, step=0.0005, format="%.4f")
num_sites = st.sidebar.slider("Number of Sites to Randomly Select", 1, 30, 6)
generate = st.sidebar.button("⚙️ Generate Grid + Random Sites")

# === Session State to Hold Results ===
if "site_coords" not in st.session_state:
    st.session_state.site_coords = []
if "lake_polygon" not in st.session_state:
    st.session_state.lake_polygon = None

# === Drawing Map ===
m = folium.Map(location=center_latlon, zoom_start=15, tiles="Esri.WorldImagery")
Draw(export=True).add_to(m)
draw_data = st_folium(m, height=600, width=1000)

# === Generate Grid + Sites ===
if generate:
    drawings = draw_data.get("all_drawings", [])
    if not drawings:
        st.error("⚠️ Please draw a polygon to represent the lake boundary.")
    else:
        shape = drawings[0]
        if shape["geometry"]["type"] != "Polygon":
            st.error("⚠️ You must draw a polygon, not a point or line.")
        else:
            coords = shape["geometry"]["coordinates"][0]
            try:
                poly = Polygon(coords)
                st.session_state.lake_polygon = poly

                # Generate uniform grid
                minx, miny, maxx, maxy = poly.bounds
                grid_cells = []
                x = minx
                while x < maxx:
                    y = miny
                    while y < maxy:
                        cell = box(x, y, x + grid_size, y + grid_size)
                        if poly.intersects(cell):
                            grid_cells.append(cell)
                        y += grid_size
                    x += grid_size

                st.info(f"✅ Generated {len(grid_cells)} grid cells inside the polygon.")

                # Random selection
                selected_cells = random.sample(grid_cells, min(len(grid_cells), num_sites))
                st.session_state.site_coords = [(cell.centroid.y, cell.centroid.x) for cell in selected_cells]
                st.success("✅ Sampling sites selected! Scroll down to view.")

            except Exception as e:
                st.error(f"❌ Failed to process shape: {e}")

# === Display Final Map with Grid + Points ===
if st.session_state.lake_polygon:
    result_map = folium.Map(location=[st.session_state.lake_polygon.centroid.y,
                                      st.session_state.lake_polygon.centroid.x],
                            zoom_start=15, tiles="Esri.WorldImagery")

    # Add polygon
    folium.GeoJson(st.session_state.lake_polygon, name="Drawn Reservoir").add_to(result_map)

    # Add site markers
    for i, (lat, lon) in enumerate(st.session_state.site_coords):
        folium.Marker(
            location=[lat, lon],
            popup=f"Site {i+1}",
            icon=folium.Icon(color="blue")
        ).add_to(result_map)

    st.subheader("📍 Final Sample Site Map")
    st_folium(result_map, height=600, width=1000)

    # Export CSV
    df = pd.DataFrame(st.session_state.site_coords, columns=["Latitude", "Longitude"])
    st.subheader("📥 Download Site Coordinates")
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False),
        file_name="random_sites.csv",
        mime="text/csv"
    )
