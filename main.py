import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Polygon, box
import random
import pandas as pd

st.set_page_config(page_title="Draw + Randomize Sites", layout="wide")
st.title("🎣 Reservoir Sampling Randomizer")

# Sidebar
st.sidebar.subheader("🔧 Sampling Parameters")
grid_size = st.sidebar.number_input("Grid Size (degrees ~0.001 ~110m)", value=0.001, step=0.0005, format="%.4f")
num_sites = st.sidebar.slider("Number of Sites to Select", 1, 30, 5)
generate = st.sidebar.button("⚙️ Generate Grid and Random Sites")

# Map setup
center_lat, center_lon = 40.53, -109.55  # center around Steinaker by default
m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="Esri.WorldImagery")

# Draw tool
draw = Draw(export=True, draw_options={"polyline": False, "circle": False, "circlemarker": False})
draw.add_to(m)

st.subheader("🗺️ Draw the Reservoir Boundary")
st_data = st_folium(m, height=600, width=1000)

if generate:
    if not st_data.get("all_drawings"):
        st.error("Please draw a polygon to represent the reservoir boundary before generating.")
    else:
        shape = st_data["all_drawings"][0]["geometry"]
        if shape["type"] != "Polygon":
            st.error("You must draw a polygon.")
        else:
            # Convert drawn shape to Shapely polygon
            coords = shape["coordinates"][0]
            poly = Polygon(coords)

            st.success("✅ Boundary drawn successfully. Generating grid...")

            # Generate grid covering bounding box of polygon
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

            # Convert to GeoDataFrame
            grid_gdf = gpd.GeoDataFrame(geometry=grid_cells)

            # Random sample of grid cells
            if num_sites > len(grid_cells):
                st.warning(f"Only {len(grid_cells)} cells available inside polygon. Selecting all.")
                selected_cells = grid_cells
            else:
                selected_cells = random.sample(grid_cells, num_sites)

            selected_centroids = [(round(cell.centroid.y, 6), round(cell.centroid.x, 6)) for cell in selected_cells]

            # Display sites on map
            result_map = folium.Map(location=[poly.centroid.y, poly.centroid.x], zoom_start=15, tiles="Esri.WorldImagery")
            folium.GeoJson(poly, name="Boundary").add_to(result_map)

            for i, (lat, lon) in enumerate(selected_centroids):
                folium.Marker(
                    location=[lat, lon],
                    popup=f"Site {i+1}",
                    icon=folium.Icon(color="blue")
                ).add_to(result_map)

            st.subheader("📍 Final Sampling Sites")
            st_folium(result_map, height=600, width=1000)

            # Export CSV
            df = pd.DataFrame(selected_centroids, columns=["Latitude", "Longitude"])
            st.download_button(
                label="📥 Download Sites as CSV",
                data=df.to_csv(index=False),
                file_name="random_sampling_sites.csv",
                mime="text/csv"
            )
