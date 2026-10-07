import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="PDNA Housing Dashboard", page_icon="🏠", layout="wide")

@st.cache_data(ttl=300)
def load_kobo():
    k=st.secrets["kobo"]; url=f'{k["base_url"].rstrip("/")}/api/v2/assets/{k["asset_uid"]}/data/'
    headers={"Authorization":f'Token {k["token"]}'}
    rows=[]
    while url:
        r=requests.get(url,headers=headers,params={"limit":1000} if not rows else None,timeout=30)
        r.raise_for_status(); p=r.json()
        if isinstance(p,dict) and "results" in p: rows += p["results"]; url=p.get("next")
        elif isinstance(p,list): rows += p; url=None
        else: raise ValueError("Unexpected Kobo API response")
    return pd.DataFrame(rows)

def pick(d,*names):
    for n in names:
        if n in d.columns: return d[n]
    return pd.Series([""]*len(d),index=d.index)

try: raw=load_kobo()
except Exception as e:
    st.error("Could not connect to KoboToolbox. Check Streamlit Secrets and Kobo permissions."); st.exception(e); st.stop()
if raw.empty: st.warning("The Kobo project has no submissions."); st.stop()

df=pd.DataFrame(index=raw.index)
df["housing_code"]=pick(raw,"housing_code").fillna("").astype(str)
df["date"]=pick(raw,"date").fillna("").astype(str)
df["type_construction"]=pick(raw,"type_construction").fillna("").astype(str)
df["classification"]=pick(raw,"summary_classification","clasification_damage").fillna("").astype(str)
for target,names in {"building_area":("building_area",),"damage":("summary_damage","direct_damage"),"losses":("summary_losses","total_losses"),"impact":("summary_impact","total_impact")}.items():
    df[target]=pd.to_numeric(pick(raw,*names),errors="coerce").fillna(0)
if "_location_gps_latitude" in raw and "_location_gps_longitude" in raw:
    df["latitude"]=pd.to_numeric(raw["_location_gps_latitude"],errors="coerce")
    df["longitude"]=pd.to_numeric(raw["_location_gps_longitude"],errors="coerce")
else:
    gps=pick(raw,"location_gps").fillna("").astype(str).str.split()
    df["latitude"]=pd.to_numeric(gps.str[0],errors="coerce"); df["longitude"]=pd.to_numeric(gps.str[1],errors="coerce")

st.title("PDNA Housing Dashboard")
st.caption("Saint Vincent and the Grenadines · Live connection to KoboToolbox")
st.success(f"Connected to KoboToolbox · {len(df):,} housing assessment(s) loaded · cache refresh up to 5 minutes")

with st.sidebar:
    st.header("Filters")
    classes=sorted(x for x in df.classification.unique() if x); types=sorted(x for x in df.type_construction.unique() if x)
    sc=st.multiselect("Damage classification",classes,default=classes); stp=st.multiselect("Construction typology",types,default=types)
    if st.button("Refresh Kobo data"): st.cache_data.clear(); st.rerun()
f=df.copy()
if classes: f=f[f.classification.isin(sc)]
if types: f=f[f.type_construction.isin(stp)]

cols=st.columns(5)
for c,label,val in zip(cols,["Housing Assessments","Total Damage","Total Losses","Total Impact","Average Damage"],[len(f),f.damage.sum(),f.losses.sum(),f.impact.sum(),f.damage.mean() if len(f) else 0]):
    c.metric(label,f"{val:,.0f}" if label=="Housing Assessments" else f"{val:,.2f}")

left,right=st.columns([1.7,1])
with left:
    st.subheader("Housing Damage Map")
    mdf=f.dropna(subset=["latitude","longitude"])
    if len(mdf):
        m=folium.Map([mdf.latitude.mean(),mdf.longitude.mean()],zoom_start=14)
        colors={"No damage":"green","Light":"blue","Mild":"orange","Severe":"red","Destroyed":"darkred"}
        for _,r in mdf.iterrows():
            pop=f"<b>Housing:</b> {r.housing_code}<br><b>Classification:</b> {r.classification}<br><b>Typology:</b> {r.type_construction}<br><b>Damage:</b> {r.damage:,.2f}<br><b>Losses:</b> {r.losses:,.2f}<br><b>Total impact:</b> {r.impact:,.2f}"
            folium.CircleMarker([r.latitude,r.longitude],radius=8,popup=pop,tooltip=f"{r.housing_code} · {r.classification}",color=colors.get(r.classification,"gray"),fill=True).add_to(m)
        st_folium(m,height=460,use_container_width=True,returned_objects=[])
with right:
    st.subheader("Damage Classification")
    st.bar_chart(f.classification.value_counts().reindex(["No damage","Light","Mild","Severe","Destroyed"],fill_value=0),horizontal=True)
    st.subheader("Construction Typology"); st.bar_chart(f.type_construction.value_counts(),horizontal=True)

st.subheader("Housing Assessments")
t=f[["housing_code","date","type_construction","building_area","classification","damage","losses","impact"]].copy()
t.columns=["Housing code","Date","Construction typology","Area (sq ft)","Damage classification","Damage","Losses","Total impact"]
st.dataframe(t,use_container_width=True,hide_index=True)
st.caption("Source: KoboToolbox · Credentials stored privately in Streamlit Secrets · Data cache: 5 minutes.")
