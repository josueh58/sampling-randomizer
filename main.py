import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Polygon, box
import random
import pandas as pd

st.set_page_config(page_title="Reservoir Sampling Grid", layout="wide")
st.title("🎣 Reservoir Sampling Randomizer v2.7")

# === Known reservoirs for map centering
RESERVOIRS = {
    "Steinaker Reservoir": [40.525, -109.55],
    "Red Fleet Reservoir": [40.625, -109.465],
    "Big Sandwash Reservoir": [40.314, -110.058]
}

# === Sidebar controls
st.sidebar.subheader("📍 Reservoir + Sampling Settings")
selected_res = st.sidebar.selectbox("Center Map On", list(RESERVOIRS.keys()))
center_latlon = RESERVOIRS[selected_res]

grid_size = st.sidebar.number_input("Grid Cell Size (degrees ~0.001 ≈ 110m)", value=0.001, step=0.0005, format="%.4f")
num_sites = st.sidebar.slider("Number of Random Sample Sites", 1, 30, 6)
generate = st.sidebar.button("⚙️ Generate Sites")

# === Session state setup
if "lake_polygon" not in st.session_state:
    st.session_state.lake_polygon = None
if "clipped_grid" not in st.session_state:
    st.session_state.clipped_grid = None
if "site_coords" not in st.session_state:
    st.session_state.site_coords = []

# === Drawing map
m = folium.Map(location=center_latlon, zoom_start=15, tiles="Esri.WorldImagery")
Draw(export=True).add_to(m)
draw_data = st_folium(m, height=600, width=1000)

# === Handle drawing + grid generation
if generate:
    drawings = draw_data.get("all_drawings", [])
    if not drawings:
        st.error("⚠️ Please draw a polygon representing the lake.")
    else:
        shape = drawings[0]
        if shape["geometry"]["type"] != "Polygon":
            st.error("⚠️ Only polygon shapes are accepted.")
        else:
            try:
                # Convert to Shapely polygon
                coords = shape["geometry"]["coordinates"][0]
                lake_poly = Polygon(coords)
                st.session_state.lake_polygon = lake_poly

                # Generate square grid over bounding box
                minx, miny, maxx, maxy = lake_poly.bounds
                grid_cells = []
                x = minx
                while x < maxx:
                    y = miny
                    while y < maxy:
                        cell = box(x, y, x + grid_size, y + grid_size)
                        grid_cells.append(cell)
                        y += grid_size
                    x += grid_size

                # Convert to GeoDataFrame
                grid_gdf = gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:4326")
                lake_gdf = gpd.GeoDataFrame(geometry=[lake_poly], crs="EPSG:4326")

                # Clip grid to lake polygon
                clipped = gpd.overlay(grid_gdf, lake_gdf, how="intersection")
                st.session_state.clipped_grid = clipped

                st.success(f"✅ {len(clipped)} grid cells intersect the lake boundary.")

                # Randomly select N cells and get centroids
                selected = clipped.sample(min(len(clipped), num_sites))
                centroids = [(geom.centroid.y, geom.centroid.x) for geom in selected.geometry]
                st.session_state.site_coords = centroids

                st.success("🎯 Random sample sites selected!")

            except Exception as e:
                st.error(f"❌ Failed to generate grid: {e}")

# === Display result map
if st.session_state.lake_polygon and st.session_state.clipped_grid is not None:
    result_map = folium.Map(
        location=[st.session_state.lake_polygon.centroid.y,
                  st.session_state.lake_polygon.centroid.x],
        zoom_start=15,
        tiles="Esri.WorldImagery"
    )

    # Add polygon
    folium.GeoJson(st.session_state.lake_polygon, name="Lake Boundary").add_to(result_map)

    # Add clipped grid
    for _, row in st.session_state.clipped_grid.iterrows():
        folium.GeoJson(row.geometry, style_function=lambda x: {
            "color": "gray", "weight": 1, "fillOpacity": 0
        }).add_to(result_map)

    # Highlight selected grid cells
    selected_polys = gpd.GeoSeries([Polygon([(pt[1]-grid_size/2, pt[0]-grid_size/2),
                                             (pt[1]+grid_size/2, pt[0]-grid_size/2),
                                             (pt[1]+grid_size/2, pt[0]+grid_size/2),
                                             (pt[1]-grid_size/2, pt[0]+grid_size/2)])
                                    for pt in st.session_state.site_coords], crs="EPSG:4326")
    for geom in selected_polys:
        folium.GeoJson(geom, style_function=lambda x: {
            "color": "blue", "weight": 2, "fillOpacity": 0.2
        }).add_to(result_map)

    # Add sample site markers
    for i, (lat, lon) in enumerate(st.session_state.site_coords):
        folium.Marker([lat, lon], popup=f"Site {i+1}", icon=folium.Icon(color="blue")).add_to(result_map)

    st.subheader("📍 Final Sample Site Map")
    st_folium(result_map, height=600, width=1000)

    # Download CSV
    df = pd.DataFrame(st.session_state.site_coords, columns=["Latitude", "Longitude"])
    st.subheader("📥 Export Coordinates")
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False),
        file_name="random_sites.csv",
        mime="text/csv"
    )


