import os

import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
st.set_page_config(page_title="Claims review", layout="wide")
st.title("Synthetic claims review")
st.caption("Demo only: use synthetic or public sample documents, never real patient data.")

uploaded = st.file_uploader("Upload a claim form or letter", type=["txt", "pdf"])
if uploaded and st.button("Process document"):
    try:
        response = requests.post(f"{API}/claims", files={"file": (uploaded.name, uploaded.getvalue())}, timeout=45)
        response.raise_for_status()
        st.success(f"Processed claim #{response.json()['id']}")
    except requests.RequestException as exc:
        st.error(f"Processing failed: {exc}")

try:
    stats = requests.get(f"{API}/stats", timeout=10).json()
    claims = requests.get(f"{API}/claims", params={"limit": 500}, timeout=10).json()
    a, b = st.columns(2)
    a.metric("Processed (latest 500)", stats["total_in_window"])
    b.metric("Flagged (latest 500)", stats["flagged_in_window"])
    if stats["flag_counts"]:
        st.subheader("Reasons for review")
        st.bar_chart(pd.Series(stats["flag_counts"]))
    st.subheader("Recent documents")
    rows = [{"id": c["id"], "file": c["filename"], "claim_id": c["fields"]["claim_id"],
             "amount": c["fields"]["amount"], "flags": ", ".join(f["code"] for f in c["flags"]),
             "processed_at": c["created_at"]} for c in claims]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if claims:
        selected = st.selectbox("Inspect processed document", [c["id"] for c in claims])
        st.json(next(c for c in claims if c["id"] == selected))
except (requests.RequestException, ValueError, KeyError) as exc:
    st.warning(f"API unavailable: {exc}")
