# streamlit_app.py
import streamlit as st
import folium
from streamlit_folium import st_folium
import random
import pandas as pd
import smtplib
from email.mime.text import MIMEText

st.set_page_config(page_title="Reservoir Sampling Randomizer", layout="wide")
st.title("🎣 Reservoir Sampling Site Randomizer")

# === SETTINGS ===
# Example reservoir bounds (approximate) for Steinaker Reservoir
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

reservoir = st.selectbox("Select Reservoir", list(RESERVOIRS.keys()))
num_sites = st.slider("Number of Sampling Sites", 1, 20, 6)

bounds = RESERVOIRS[reservoir]
random_points = []

if st.button("🎲 Generate Random Sampling Sites"):
    for _ in range(num_sites):
        lat = random.uniform(bounds["lat_min"], bounds["lat_max"])
        lon = random.uniform(bounds["lon_min"], bounds["lon_max"])
        random_points.append((lat, lon))

    df_coords = pd.DataFrame(random_points, columns=["Latitude", "Longitude"])
    st.dataframe(df_coords)

    # Create a folium map with random points
    m = folium.Map(
        location=[(bounds["lat_min"] + bounds["lat_max"]) / 2,
                  (bounds["lon_min"] + bounds["lon_max"]) / 2],
        zoom_start=15,
        tiles="Esri.WorldImagery"  # satellite view
    )

    for idx, (lat, lon) in enumerate(random_points):
        folium.Marker(
            location=[lat, lon],
            popup=f"Site {idx + 1}",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)

    st_folium(m, width=1000, height=600)

    # Export download
    st.download_button(
        "📥 Download Coordinates CSV",
        data=df_coords.to_csv(index=False),
        file_name="sampling_sites.csv",
        mime="text/csv"
    )

    # Optional: Send via Email
    with st.expander("📧 Email Coordinates"):
        to_email = st.text_input("Send to email:")
        if st.button("Send Email"):
            msg = MIMEText(df_coords.to_csv(index=False))
            msg["Subject"] = f"Sampling Coordinates for {reservoir}"
            msg["From"] = "your_email@example.com"
            msg["To"] = to_email

            try:
                with smtplib.SMTP("smtp.gmail.com", 587) as server:
                    server.starttls()
                    server.login("your_email@example.com", "your_password")
                    server.send_message(msg)
                    st.success("Email sent successfully!")
            except Exception as e:
                st.error(f"Failed to send email: {e}")
