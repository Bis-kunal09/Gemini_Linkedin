import json
import pandas as pd
import plotly.express as px
import streamlit as st

# Set Page Config
st.set_page_config(
    page_title="Data Engineer Job Market Dashboard",
    page_icon="📊",
    layout="wide"
)

# Title & Header
st.title("📊 Live Data Engineer Market Intelligence")
st.markdown("Real-time tracking and market insights for **Data Engineer** job postings.")

# Load Data
@st.cache_data(ttl=600)  # Refresh cache every 10 mins
def load_data():
    try:
        with open("jobs.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        if not df.empty and "scraped_at" in df.columns:
            df["scraped_at"] = pd.to_datetime(df["scraped_at"])
        return df
    except Exception as e:
        st.error(f"Error loading jobs.json: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("No job data available yet. Run the scraper to populate jobs.json.")
    st.stop()

# --- TOP METRICS CARDS ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Jobs Tracked", len(df))
with col2:
    unique_companies = df["company"].nunique() if "company" in df.columns else 0
    st.metric("Hiring Companies", unique_companies)
with col3:
    latest_date = df["scraped_at"].dt.strftime("%Y-%m-%d %H:%M").max() if "scraped_at" in df.columns else "N/A"
    st.metric("Last Updated (UTC)", latest_date)
with col4:
    remote_count = df["location"].str.contains("Remote", case=False, na=False).sum() if "location" in df.columns else 0
    st.metric("Remote Postings", remote_count)

st.divider()

# --- CHARTS SECTION ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🏢 Top Hiring Companies")
    top_companies = df["company"].value_counts().head(10).reset_index()
    top_companies.columns = ["Company", "Openings"]
    fig_comp = px.bar(
        top_companies, 
        x="Openings", 
        y="Company", 
        orientation="h",
        color="Openings",
        color_continuous_scale="Blues",
        text_auto=True
    )
    fig_comp.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
    st.plotly_chart(fig_comp, use_container_width=True)

with col_right:
    st.subheader("🛠️ Most In-Demand Skills / Tech Stack")
    if "skills" in df.columns:
        # Flatten list of skills
        all_skills = [skill for sublist in df["skills"].dropna() for skill in sublist]
        if all_skills:
            skills_df = pd.Series(all_skills).value_counts().reset_index()
            skills_df.columns = ["Skill", "Count"]
            fig_skills = px.pie(
                skills_df.head(8), 
                values="Count", 
                names="Skill", 
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_skills, use_container_width=True)
        else:
            st.info("No skill tags extracted yet.")

# --- SEARCHABLE DATA TABLE ---
st.divider()
st.subheader("🔍 Explore Latest Job Listings")

# Filters
search_query = st.text_input("Search by Job Title or Company", "")
if search_query:
    filtered_df = df[
        df["title"].str.contains(search_query, case=False, na=False) |
        df["company"].str.contains(search_query, case=False, na=False)
    ]
else:
    filtered_df = df

st.dataframe(
    filtered_df[["title", "company", "location", "posted_date", "link"]],
    column_config={
        "link": st.column_config.LinkColumn("Apply Link", display_text="View on LinkedIn")
    },
    use_container_width=True,
    hide_index=True
)
