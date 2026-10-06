# PDNA Housing Dashboard MVP

This MVP uses the two test Housing records exported from KoboToolbox on 2026-10-06.

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run:

   pip install -r requirements.txt
   streamlit run app.py

The browser will open the dashboard.

## Current MVP
- Housing Assessments KPI
- Total Damage, Losses and Impact
- Average Damage
- Interactive GPS map
- Damage classification chart
- Construction typology chart
- Filters
- Public-safe assessment table (interviewee names are omitted)

The two current GPS points are test records collected in Guatemala.

## Next stage
Replace the embedded records in app.py with a read-only KoboToolbox API connection and cache/refresh the data approximately every five minutes.
