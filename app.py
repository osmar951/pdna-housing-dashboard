import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="PDNA Housing Dashboard", page_icon="🏠", layout="wide")

DATA = [{'housing_code': 'Big street 22', 'date': '2026-10-06', 'latitude': 14.610297, 'longitude': -90.661599, 'type_construction': 'wood walls and sheet metal', 'building_area': 950, 'replacement_value': 114000.0, 'classification': 'Mild', 'damage': 49380.0, 'losses': 1728.3, 'impact': 51108.3}, {'housing_code': 'Long Ave 564', 'date': '2026-10-06', 'latitude': 14.610282, 'longitude': -90.661556, 'type_construction': 'block walls and concrete', 'building_area': 1520, 'replacement_value': 334400.0, 'classification': 'Light', 'damage': 86944.0, 'losses': 3563.04, 'impact': 90507.04}]
df = pd.DataFrame(DATA)

st.title("PDNA Housing Dashboard")
st.caption("Saint Vincent and the Grenadines · MVP with test records collected in Guatemala")
st.info("TEST DATA: the current GPS points are in Guatemala. They are used only to validate the dashboard workflow.")

with st.sidebar:
    st.header("Filters")
    classes = sorted(df["classification"].unique())
    types = sorted(df["type_construction"].unique())
    selected_classes = st.multiselect("Damage classification", classes, default=classes)
    selected_types = st.multiselect("Construction typology", types, default=types)

f = df[df["classification"].isin(selected_classes) & df["type_construction"].isin(selected_types)].copy()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Housing Assessments", f"{len(f):,}")
c2.metric("Total Damage", f"$ {f['damage'].sum():,.2f}")
c3.metric("Total Losses", f"$ {f['losses'].sum():,.2f}")
c4.metric("Total Impact", f"$ {f['impact'].sum():,.2f}")
c5.metric("Average Damage", f"$ {(f['damage'].mean() if len(f) else 0):,.2f}")

left, right = st.columns([1.7, 1])

with left:
    st.subheader("Housing Damage Map")
    if len(f):
        center = [f["latitude"].mean(), f["longitude"].mean()]
        m = folium.Map(location=center, zoom_start=16, tiles="OpenStreetMap")
        class_colors = {
            "No damage": "green",
            "Light": "blue",
            "Mild": "orange",
            "Severe": "red",
            "Destroyed": "darkred",
        }
        for _, r in f.iterrows():
            popup = f"""
            <b>Housing:</b> {r['housing_code']}<br>
            <b>Classification:</b> {r['classification']}<br>
            <b>Typology:</b> {r['type_construction']}<br>
            <b>Damage:</b> ${r['damage']:,.2f}<br>
            <b>Losses:</b> ${r['losses']:,.2f}<br>
            <b>Total impact:</b> ${r['impact']:,.2f}
            """
            folium.CircleMarker(
                location=[r["latitude"], r["longitude"]],
                radius=9,
                popup=folium.Popup(popup, max_width=330),
                tooltip=f"{r['housing_code']} · {r['classification']}",
                color=class_colors.get(r["classification"], "gray"),
                fill=True,
                fill_opacity=0.85,
            ).add_to(m)
        st_folium(m, height=460, use_container_width=True, returned_objects=[])
    else:
        st.warning("No records match the selected filters.")

with right:
    st.subheader("Damage Classification")
    order = ["No damage", "Light", "Mild", "Severe", "Destroyed"]
    counts = f["classification"].value_counts().reindex(order, fill_value=0)
    st.bar_chart(counts, horizontal=True)

    st.subheader("Construction Typology")
    typ = f["type_construction"].value_counts()
    st.bar_chart(typ, horizontal=True)

st.subheader("Housing Assessments")
public_cols = [
    "housing_code", "date", "type_construction", "building_area",
    "classification", "damage", "losses", "impact"
]
display = f[public_cols].rename(columns={
    "housing_code": "Housing code",
    "date": "Date",
    "type_construction": "Construction typology",
    "building_area": "Area (sq ft)",
    "classification": "Damage classification",
    "damage": "Damage",
    "losses": "Losses",
    "impact": "Total impact",
})
st.dataframe(
    display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Damage": st.column_config.NumberColumn(format="$ %.2f"),
        "Losses": st.column_config.NumberColumn(format="$ %.2f"),
        "Total impact": st.column_config.NumberColumn(format="$ %.2f"),
    },
)

st.caption("MVP source: KoboToolbox XLSX export. Next stage: replace embedded test data with Kobo API data and refresh approximately every five minutes.")
