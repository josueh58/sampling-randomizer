import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import geopandas as gpd
from shapely.geometry import Polygon, box
import random
import pandas as pd
from shapely.ops import transform
import pyproj
import math

st.set_page_config(page_title="Reservoir Sampling Grid", layout="wide")
st.title("🎣 Reservoir Sampling Randomizer v2.8")

# === Map centers for convenience
RESERVOIRS = {
    "Steinaker Reservoir": [40.525, -109.55],
    "Red Fleet Reservoir": [40.625, -109.465],
    "Big Sandwash Reservoir": [40.314, -110.058]
}

# === Sidebar controls
st.sidebar.subheader("📍 Reservoir + Sampling Settings")
selected_res = st.sidebar.selectbox("Center Map On", list(RESERVOIRS.keys()))
center_latlon = RESERVOIRS[selected_res]

num_sites = st.sidebar.slider("Number of Random Sample Sites", 1, 50, 6)
generate = st.sidebar.button("⚙️ Generate Sites")

# === Session state setup
if "lake_polygon" not in st.session_state:
    st.session_state.lake_polygon = None
if "clipped_grid" not in st.session_state:
    st.session_state.clipped_grid = None
if "site_coords" not in st.session_state:
    st.session_state.site_coords = []
if "grid_size_deg" not in st.session_state:
    st.session_state.grid_size_deg = None

# === Drawing map
m = folium.Map(location=center_latlon, zoom_start=15, tiles="Esri.WorldImagery")
Draw(export=True).add_to(m)
draw_data = st_folium(m, height=600, width=1000)

# === Grid generation logic
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
                coords = shape["geometry"]["coordinates"][0]
                lake_poly = Polygon(coords)
                st.session_state.lake_polygon = lake_poly

                # Project polygon to UTM for accurate area calc
                project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32612", always_xy=True).transform
                lake_poly_utm = transform(project, lake_poly)
                lake_area_m2 = lake_poly_utm.area
                lake_area_ha = lake_area_m2 / 10000
                st.sidebar.markdown(f"🧮 Lake Area: **{lake_area_ha:.1f} ha**")

                # Auto-calculate grid cell size
                target_cells = num_sites * 2
                cell_area_m2 = lake_area_m2 / target_cells
                cell_size_m = math.sqrt(cell_area_m2)
                meters_per_degree = 111000  # approx
                grid_size_deg = cell_size_m / meters_per_degree
                st.session_state.grid_size_deg = grid_size_deg

                st.sidebar.markdown(f"📐 Auto Grid Cell Size: **{grid_size_deg:.4f}°**")

                # Generate square grid
                minx, miny, maxx, maxy = lake_poly.bounds
                grid_cells = []
                x = minx
                while x < maxx:
                    y = miny
                    while y < maxy:
                        cell = box(x, y, x + grid_size_deg, y + grid_size_deg)
                        grid_cells.append(cell)
                        y += grid_size_deg
                    x += grid_size_deg

                grid_gdf = gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:4326")
                lake_gdf = gpd.GeoDataFrame(geometry=[lake_poly], crs="EPSG:4326")

                # Clip grid to lake polygon
                clipped = gpd.overlay(grid_gdf, lake_gdf, how="intersection")
                st.session_state.clipped_grid = clipped

                st.success(f"✅ {len(clipped)} grid cells intersect the lake boundary.")

                # Random selection of sites
                selected = clipped.sample(min(len(clipped), num_sites))
                centroids = [(geom.centroid.y, geom.centroid.x) for geom in selected.geometry]
                st.session_state.site_coords = centroids

                st.success("🎯 Sampling sites selected!")

            except Exception as e:
                st.error(f"❌ Failed to generate grid: {e}")

# === Display results
if st.session_state.lake_polygon and st.session_state.clipped_grid is not None:
    result_map = folium.Map(
        location=[st.session_state.lake_polygon.centroid.y,
                  st.session_state.lake_polygon.centroid.x],
        zoom_start=15,
        tiles="Esri.WorldImagery"
    )

    # Add lake polygon
    folium.GeoJson(st.session_state.lake_polygon, name="Lake Boundary").add_to(result_map)

    # Add clipped grid
    for _, row in st.session_state.clipped_grid.iterrows():
        folium.GeoJson(row.geometry, style_function=lambda x: {
            "color": "gray", "weight": 1, "fillOpacity": 0
        }).add_to(result_map)

    # Highlight selected cells
    gsize = st.session_state.grid_size_deg
    selected_polys = gpd.GeoSeries([Polygon([
        (pt[1]-gsize/2, pt[0]-gsize/2),
        (pt[1]+gsize/2, pt[0]-gsize/2),
        (pt[1]+gsize/2, pt[0]+gsize/2),
        (pt[1]-gsize/2, pt[0]+gsize/2)
    ]) for pt in st.session_state.site_coords], crs="EPSG:4326")

    for geom in selected_polys:
        folium.GeoJson(geom, style_function=lambda x: {
            "color": "blue", "weight": 2, "fillOpacity": 0.2
        }).add_to(result_map)

    # Add site markers
    for i, (lat, lon) in enumerate(st.session_state.site_coords):
        folium.Marker([lat, lon], popup=f"Site {i+1}", icon=folium.Icon(color="blue")).add_to(result_map)

    st.subheader("📍 Final Sample Site Map")
    st_folium(result_map, height=600, width=1000)

    # Export CSV
    df = pd.DataFrame(st.session_state.site_coords, columns=["Latitude", "Longitude"])
    st.subheader("📥 Export Coordinates")
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False),
        file_name="random_sites.csv",
        mime="text/csv"
    )

