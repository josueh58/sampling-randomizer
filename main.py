import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Polygon, box
import random
import pandas as pd

st.set_page_config(page_title="Reservoir Sampling Grid", layout="wide")
st.title("🎣 Draw a Reservoir, Overlay a Grid, and Randomize Sites")

# Sidebar inputs
st.sidebar.subheader("📐 Grid + Randomization Settings")
grid_size = st.sidebar.number_input("Grid Cell Size (degrees ~0.001 = ~110m)", value=0.001, step=0.0005, format="%.4f")
num_sites = st.sidebar.slider("Number of Sample Sites", 1, 50, 6)
generate = st.sidebar.button("⚙️ Generate Sites from Polygon")

# Map setup
m = folium.Map(location=[40.525, -109.55], zoom_start=15, tiles="Esri.WorldImagery")
Draw(export=True).add_to(m)
st_data = st_folium(m, height=600, width=1000)

# Catch and process the polygon
if generate:
    shapes = st_data.get("all_drawings", [])
    if not shapes:
        st.error("⚠️ Please draw a polygon before clicking Generate.")
    else:
        shape = shapes[0]  # only take the first one
        if shape["geometry"]["type"] != "Polygon":
            st.error("⚠️ You must draw a polygon, not a line or point.")
        else:
            coords = shape["geometry"]["coordinates"][0]
            try:
                polygon = Polygon(coords)
                st.success("✅ Polygon successfully drawn.")

                # Generate grid cells inside bounding box of polygon
                minx, miny, maxx, maxy = polygon.bounds
                grid_cells = []
                x = minx
                while x < maxx:
                    y = miny
                    while y < maxy:
                        cell = box(x, y, x + grid_size, y + grid_size)
                        if polygon.intersects(cell):
                            grid_cells.append(cell)
                        y += grid_size
                    x += grid_size

                st.info(f"✅ {len(grid_cells)} grid cells generated inside polygon.")

                if not grid_cells:
                    st.warning("⚠️ No valid grid cells inside polygon. Try increasing the polygon size or decreasing grid resolution.")
                else:
                    # Randomly pick sample sites
                    selected_cells = random.sample(grid_cells, min(len(grid_cells), num_sites))
                    site_coords = [(cell.centroid.y, cell.centroid.x) for cell in selected_cells]

                    # Display results
                    map2 = folium.Map(location=[polygon.centroid.y, polygon.centroid.x], zoom_start=15, tiles="Esri.WorldImagery")
                    folium.GeoJson(polygon, name="Drawn Boundary").add_to(map2)

                    for i, (lat, lon) in enumerate(site_coords):
                        folium.Marker(
                            location=[lat, lon],
                            popup=f"Site {i + 1}",
                            icon=folium.Icon(color="blue")
                        ).add_to(map2)

                    st.subheader("🧭 Randomized Site Map")
                    st_folium(map2, height=600, width=1000)

                    # Export CSV
                    df = pd.DataFrame(site_coords, columns=["Latitude", "Longitude"])
                    st.subheader("📥 Download Coordinates")
                    st.download_button(
                        label="Download as CSV",
                        data=df.to_csv(index=False),
                        file_name="random_sampling_sites.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"❌ Failed to process polygon: {e}")
