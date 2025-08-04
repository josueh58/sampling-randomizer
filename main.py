import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Polygon, box
from shapely.ops import transform
import pyproj
import pandas as pd
from PIL import Image
import base64
from io import BytesIO

# ─────────────────────────────────────────────────────────────────────────────
# Function to encode and display H.A.DREAMS logo
def get_logo_base64(path="hadreams_logo.png", width=100):
    img = Image.open(path)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"""
    <div style='position: fixed; top: 10px; left: 10px; z-index: 1000;'>
        <img src="data:image/png;base64,{encoded}" width="{width}"/>
    </div>
    """

# ─────────────────────────────────────────────────────────────────────────────
# Streamlit page setup
st.set_page_config(page_title="Reservoir Sampling Tool", layout="wide")
st.markdown(get_logo_base64("hadreams_logo.png", width=100), unsafe_allow_html=True)
st.title("🎣 Reservoir Sampling Randomizer v3.0")

# ─────────────────────────────────────────────────────────────────────────────
# Reservoir centers
RESERVOIRS = {
    "Steinaker Reservoir": [40.525, -109.55],
    "Red Fleet Reservoir": [40.625, -109.465],
    "Big Sandwash Reservoir": [40.314, -110.058]
}

# Sidebar controls
st.sidebar.subheader("📍 Map Settings")
selected_res = st.sidebar.selectbox("Center Map On", list(RESERVOIRS.keys()))
center_latlon = RESERVOIRS[selected_res]
num_sites = st.sidebar.slider("🎯 Number of Random Sample Sites", 1, 50, 6)
generate = st.sidebar.button("⚙️ Generate New Grid + Sites")

# Session state
if "lake_polygon" not in st.session_state:
    st.session_state.lake_polygon = None
if "site_coords" not in st.session_state:
    st.session_state.site_coords = []
if "grid_size_m" not in st.session_state:
    st.session_state.grid_size_m = None
if "grid_size_deg" not in st.session_state:
    st.session_state.grid_size_deg = None

# ─────────────────────────────────────────────────────────────────────────────
# Initial map + drawing tool
m = folium.Map(location=center_latlon, zoom_start=15, tiles="Esri.WorldImagery")
Draw(export=True).add_to(m)
draw_data = st_folium(m, height=600, width=1000)

# ─────────────────────────────────────────────────────────────────────────────
# Grid + Site Generation
if generate:
    st.session_state.lake_polygon = None
    st.session_state.site_coords = []
    st.session_state.grid_size_m = None
    st.session_state.grid_size_deg = None

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

            # Area and grid spacing
            project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32612", always_xy=True).transform
            lake_poly_utm = transform(project, lake_poly)
            area_m2 = lake_poly_utm.area
            area_acres = area_m2 * 0.000247105
            st.sidebar.markdown(f"📏 Lake Area: **{area_acres:.1f} acres**")

            if area_acres < 300:
                grid_size_m = 61
            elif area_acres <= 800:
                grid_size_m = 91
            else:
                grid_size_m = 122

            st.session_state.grid_size_m = grid_size_m
            st.sidebar.markdown(f"📐 Grid Spacing: **{grid_size_m} m**")

            # Grid conversion
            meters_per_degree = 111000
            grid_size_deg = grid_size_m / meters_per_degree
            st.session_state.grid_size_deg = grid_size_deg

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
                st.error("❌ Grid generation failed — polygon may be too small.")
            else:
                selected_cells = grid_gdf.sample(min(num_sites, len(grid_gdf)))
                centroids = [(cell.centroid.y, cell.centroid.x) for cell in selected_cells.geometry]
                st.session_state.site_coords = centroids
                st.success("✅ Sampling sites generated!")

# ─────────────────────────────────────────────────────────────────────────────
# Display map and allow editing
if st.session_state.lake_polygon and st.session_state.site_coords:
    result_map = folium.Map(
        location=[st.session_state.lake_polygon.centroid.y,
                  st.session_state.lake_polygon.centroid.x],
        zoom_start=15,
        tiles="Esri.WorldImagery"
    )

    folium.GeoJson(st.session_state.lake_polygon, name="Lake Boundary").add_to(result_map)

    # Draw grid
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
                }).add_to(result_map)
            y += gsize
        x += gsize

    for i, (lat, lon) in enumerate(st.session_state.site_coords):
        folium.Marker(
            location=[lat, lon],
            popup=f"Site {i+1}",
            draggable=True,
            icon=folium.Icon(color="blue")
        ).add_to(result_map)

    st.subheader("🗺️ Adjust Sample Sites")
    map_response = st_folium(result_map, height=600, width=1000)

    updated_coords = []
    if map_response.get("all_drawings"):
        for obj in map_response["all_drawings"]:
            if obj["geometry"]["type"] == "Point":
                coords = obj["geometry"]["coordinates"]
                updated_coords.append((coords[1], coords[0]))
        if updated_coords:
            st.session_state.site_coords = updated_coords
            st.success("🟢 Updated site locations saved from manual edits!")

    df = pd.DataFrame(st.session_state.site_coords, columns=["Latitude", "Longitude"])
    st.subheader("📥 Download Site Coordinates")
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False),
        file_name="random_sites.csv",
        mime="text/csv"
    )
