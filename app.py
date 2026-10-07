import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="PDNA Housing Dashboard", page_icon="🏠", layout="wide")

@st.cache_data(ttl=300)
def load_kobo():
    k = st.secrets["kobo"]
    url = f'{k["base_url"].rstrip("/")}/api/v2/assets/{k["asset_uid"]}/data/'
    headers = {"Authorization": f'Token {k["token"]}'}
    rows = []
    while url:
        r = requests.get(url, headers=headers, params={"limit": 1000} if not rows else None, timeout=30)
        r.raise_for_status()
        p = r.json()
        if isinstance(p, dict) and "results" in p:
            rows += p["results"]
            url = p.get("next")
        elif isinstance(p, list):
            rows += p
            url = None
        else:
            raise ValueError("Unexpected Kobo API response")
    return pd.DataFrame(rows)

def find_col(df, field):
    # Kobo API may return fields either as "field" or "group/field".
    exact = [c for c in df.columns if c == field]
    if exact:
        return exact[0]
    suffix = [c for c in df.columns if str(c).split("/")[-1] == field]
    return suffix[0] if suffix else None

def series(df, *fields, default=""):
    for field in fields:
        c = find_col(df, field)
        if c is not None:
            return df[c]
    return pd.Series([default] * len(df), index=df.index)

try:
    raw = load_kobo()
except Exception as e:
    st.error("Could not connect to KoboToolbox. Check Streamlit Secrets and Kobo permissions.")
    st.exception(e)
    st.stop()

if raw.empty:
    st.warning("The Kobo project has no submissions.")
    st.stop()

df = pd.DataFrame(index=raw.index)
df["housing_code"] = series(raw, "housing_code").fillna("").astype(str)
df["date"] = series(raw, "date").fillna("").astype(str)
df["type_construction"] = series(raw, "type_construction").fillna("").astype(str)
df["classification"] = series(raw, "summary_classification", "clasification_damage").fillna("").astype(str)

for target, fields in {
    "building_area": ("building_area",),
    "damage": ("summary_damage", "direct_damage"),
    "losses": ("summary_losses", "total_losses"),
    "impact": ("summary_impact", "total_impact"),
}.items():
    df[target] = pd.to_numeric(series(raw, *fields, default=0), errors="coerce").fillna(0)

lat = series(raw, "_location_gps_latitude")
lon = series(raw, "_location_gps_longitude")
df["latitude"] = pd.to_numeric(lat, errors="coerce")
df["longitude"] = pd.to_numeric(lon, errors="coerce")

# Kobo API commonly returns geopoint as one space-separated field rather than split export columns.
gps = series(raw, "location_gps").fillna("").astype(str).str.split()
gps_lat = pd.to_numeric(gps.str[0], errors="coerce")
gps_lon = pd.to_numeric(gps.str[1], errors="coerce")
df["latitude"] = df["latitude"].fillna(gps_lat)
df["longitude"] = df["longitude"].fillna(gps_lon)

st.title("PDNA Housing Dashboard")
st.caption("Saint Vincent and the Grenadines · Live connection to KoboToolbox")
st.success(f"Connected to KoboToolbox · {len(df):,} housing assessment(s) loaded · cache refresh up to 5 minutes")

with st.sidebar:
    st.header("Filters")
    classes = sorted(x for x in df["classification"].unique() if x)
    types = sorted(x for x in df["type_construction"].unique() if x)
    selected_classes = st.multiselect("Damage classification", classes, default=classes)
    selected_types = st.multiselect("Construction typology", types, default=types)
    if st.button("Refresh Kobo data"):
        st.cache_data.clear()
        st.rerun()

f = df.copy()
if classes:
    f = f[f["classification"].isin(selected_classes)]
if types:
    f = f[f["type_construction"].isin(selected_types)]

cols = st.columns(5)
metrics = [
    ("Housing Assessments", f"{len(f):,}"),
    ("Total Damage", f"EC$ {f['damage'].sum():,.2f}"),
    ("Total Losses", f"EC$ {f['losses'].sum():,.2f}"),
    ("Total Impact", f"EC$ {f['impact'].sum():,.2f}"),
    ("Average Damage", f"EC$ {(f['damage'].mean() if len(f) else 0):,.2f}"),
]
for c, (label, value) in zip(cols, metrics):
    c.metric(label, value)

left, right = st.columns([1.7, 1])
with left:
    st.subheader("Housing Damage Map")
    mdf = f.dropna(subset=["latitude", "longitude"])
    mdf = mdf[(mdf["latitude"].between(-90, 90)) & (mdf["longitude"].between(-180, 180))]
    if len(mdf):
        m = folium.Map([mdf["latitude"].mean(), mdf["longitude"].mean()], zoom_start=15, tiles="OpenStreetMap")
        colors = {"No damage": "green", "Light": "blue", "Mild": "orange", "Severe": "red", "Destroyed": "darkred"}
        for _, r in mdf.iterrows():
            popup = (
                f"<b>Housing:</b> {r['housing_code']}<br>"
                f"<b>Classification:</b> {r['classification']}<br>"
                f"<b>Typology:</b> {r['type_construction']}<br>"
                f"<b>Damage:</b> EC$ {r['damage']:,.2f}<br>"
                f"<b>Losses:</b> EC$ {r['losses']:,.2f}<br>"
                f"<b>Total impact:</b> EC$ {r['impact']:,.2f}"
            )
            folium.CircleMarker(
                [r["latitude"], r["longitude"]], radius=8,
                popup=folium.Popup(popup, max_width=340),
                tooltip=f"{r['housing_code']} · {r['classification']}",
                color=colors.get(r["classification"], "gray"),
                fill=True, fill_opacity=0.85
            ).add_to(m)
        st_folium(m, height=480, use_container_width=True, returned_objects=[])
    else:
        st.info("No valid GPS coordinates are available for the selected records.")

with right:
    st.subheader("Damage Classification")
    order = ["No damage", "Light", "Mild", "Severe", "Destroyed"]
    st.bar_chart(f["classification"].value_counts().reindex(order, fill_value=0), horizontal=True)
    st.subheader("Construction Typology")
    st.bar_chart(f["type_construction"].value_counts(), horizontal=True)

st.subheader("Housing Assessments")
t = f[["housing_code", "date", "type_construction", "building_area", "classification", "damage", "losses", "impact"]].copy()
t.columns = ["Housing code", "Date", "Construction typology", "Area (sq ft)", "Damage classification", "Damage (EC$)", "Losses (EC$)", "Total impact (EC$)"]
st.dataframe(t, use_container_width=True, hide_index=True)

st.caption("Source: KoboToolbox · Currency: Eastern Caribbean dollar (EC$/XCD) · Credentials stored privately in Streamlit Secrets · Data cache: 5 minutes.")
