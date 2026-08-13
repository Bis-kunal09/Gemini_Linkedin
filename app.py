import html
import json
import os
import re
import urllib.parse
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

# ==========================================
# PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="TalentPulse | LinkedIn Job Hub",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .hero-banner {
        background: linear-gradient(135deg, #0d47a1 0%, #1976d2 50%, #0077b5 100%);
        padding: 2rem;
        border-radius: 14px;
        color: #ffffff;
        margin-bottom: 1.5rem;
    }
    .hero-title { font-size: 2rem; font-weight: 700; margin-bottom: 0.2rem; }
    .hero-subtitle { font-size: 0.95rem; opacity: 0.9; }

    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
    }
    .metric-num { font-size: 1.8rem; font-weight: 700; color: #42a5f5; }
    .metric-title { font-size: 0.8rem; color: #9e9e9e; text-transform: uppercase; }

    .job-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.3rem;
        margin-bottom: 0.9rem;
    }
    .job-card:hover { border-color: #0077b5; }
    .job-title { font-size: 1.2rem; font-weight: 600; color: #64b5f6; }
    .company-sub { font-size: 0.95rem; color: #e0e0e0; margin-bottom: 0.4rem; }

    .tag {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-right: 0.3rem;
        margin-bottom: 0.3rem;
    }
    .tag-skill { background: rgba(255, 152, 0, 0.15); color: #ffb74d; }
    .tag-loc { background: rgba(33, 150, 243, 0.15); color: #64b5f6; }
    .tag-remote { background: rgba(156, 39, 176, 0.15); color: #ce93d8; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

TECH_SKILLS = [
    "Python", "Java", "C++", "C#", "Go", "Rust", "JavaScript", "TypeScript",
    "React", "Angular", "Vue", "Node.js", "FastAPI", "Django", "Flask",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "CI/CD",
    "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Pandas", "Spark"
]

# ==========================================
# CACHED DATA & UTILITIES
# ==========================================
@st.cache_data
def load_jobs_data(filepath="jobs.json"):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def extract_pdf_text(uploaded_file):
    if not PYPDF_AVAILABLE:
        return ""
    try:
        reader = pypdf.PdfReader(uploaded_file)
        return "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
    except Exception:
        return ""

def calculate_local_ats_score(resume_text: str, job_text: str) -> tuple:
    if not resume_text or not job_text:
        return 0, [], []
    
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([resume_text, job_text])
    sim_score = int(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0] * 100)
    
    resume_skills = {s for s in TECH_SKILLS if re.search(rf"\b{re.escape(s)}\b", resume_text, re.I)}
    job_skills = {s for s in TECH_SKILLS if re.search(rf"\b{re.escape(s)}\b", job_text, re.I)}
    
    matched = sorted(list(resume_skills.intersection(job_skills)))
    missing = sorted(list(job_skills.difference(resume_skills)))
    
    skill_match_ratio = (len(matched) / len(job_skills)) * 100 if job_skills else 50
    final_score = int(0.5 * sim_score + 0.5 * skill_match_ratio)
    return min(100, max(0, final_score)), matched, missing

if "applications" not in st.session_state:
    st.session_state["applications"] = {}
if "saved_ids" not in st.session_state:
    st.session_state["saved_ids"] = set()

# ==========================================
# MAIN APP HEADER
# ==========================================
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">💼 TalentPulse Job Board</div>
    <div class="hero-subtitle">Fast, local LinkedIn job filtering, ATS resume matching, and application pipeline management.</div>
</div>
""", unsafe_allow_html=True)

jobs = load_jobs_data("jobs.json")
if not jobs:
    st.warning("No jobs found in `jobs.json`. Run `python scraper.py` to fetch job listings.")
    st.stop()

df = pd.DataFrame(jobs)
if "skills" not in df.columns:
    df["skills"] = [[] for _ in range(len(df))]

# Metric Cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-num">{len(df)}</div><div class="metric-title">Available Roles</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-num">{df["company"].nunique()}</div><div class="metric-title">Companies</div></div>', unsafe_allow_html=True)
with c3:
    rem_count = len(df[df["location"].str.contains("Remote", case=False, na=False)])
    st.markdown(f'<div class="metric-card"><div class="metric-num">{rem_count}</div><div class="metric-title">Remote Roles</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-num">{len(st.session_state["saved_ids"])}</div><div class="metric-title">Saved Jobs</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tab_browse, tab_ats, tab_outreach, tab_charts, tab_kanban = st.tabs([
    "🔍 Browse Jobs",
    "📄 Local ATS Resume Matcher",
    "✉️ Networking Templates",
    "📊 Market Insights",
    "📌 Application Pipeline"
])

# ----------------- TAB 1: BROWSE JOBS -----------------
with tab_browse:
    b_col1, b_col2, b_col3, b_col4 = st.columns([3, 2, 2, 2])
    with b_col1:
        query = st.text_input("Search Roles or Companies", placeholder="e.g. Python, Backend, Stripe...")
    with b_col2:
        locations = ["All"] + sorted(list(df["location"].dropna().unique()))
        loc_filter = st.selectbox("Location", locations)
    with b_col3:
        all_skills_flat = sorted(list({s for sub in df["skills"] if isinstance(sub, list) for s in sub}))
        skill_filter = st.selectbox("Required Skill", ["All"] + all_skills_flat)
    with b_col4:
        sort_by = st.selectbox("Sort By", ["Newest", "Company (A-Z)", "Title (A-Z)"])

    filtered = df.copy()
    if query:
        q_reg = f"(?i){re.escape(query)}"
        filtered = filtered[filtered["title"].str.contains(q_reg, na=False) | filtered["company"].str.contains(q_reg, na=False)]
    if loc_filter != "All":
        filtered = filtered[filtered["location"] == loc_filter]
    if skill_filter != "All":
        filtered = filtered[filtered["skills"].apply(lambda sl: skill_filter in sl if isinstance(sl, list) else False)]

    if sort_by == "Company (A-Z)":
        filtered = filtered.sort_values(by="company")
    elif sort_by == "Title (A-Z)":
        filtered = filtered.sort_values(by="title")

    st.download_button(
        label="📥 Export Filtered Jobs (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="linkedin_jobs.csv",
        mime="text/csv"
    )

    for idx, row in filtered.iterrows():
        jid = str(row.get("id", idx))
        is_remote = "Remote" in str(row.get("location", ""))
        recruiter_search_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(row.get('company', '') + ' recruiter')}"

        skills_pills = "".join([f'<span class="tag tag-skill">{s}</span>' for s in row.get("skills", [])[:5]])
        rem_pill = '<span class="tag tag-remote">🌐 Remote</span>' if is_remote else ""

        st.markdown(f"""
        <div class="job-card">
            <div style="display: flex; justify-content: space-between;">
                <div>
                    <div class="job-title">{html.escape(str(row.get('title')))}</div>
                    <div class="company-sub">🏢 {html.escape(str(row.get('company')))} &nbsp;•&nbsp; 📍 {html.escape(str(row.get('location')))} &nbsp;•&nbsp; ⏱️ {html.escape(str(row.get('date_posted', 'Recent')))}</div>
                </div>
                <div>
                    <a href="{row.get('link', '#')}" target="_blank" style="padding: 6px 14px; background:#0077b5; color:#fff; border-radius:6px; text-decoration:none; font-size:0.85rem;">Apply on LinkedIn ↗</a>
                </div>
            </div>
            <div style="margin: 0.5rem 0;">{rem_pill}{skills_pills}</div>
            <p style="font-size:0.85rem; color:#aaa; margin: 0.3rem 0;">{html.escape(str(row.get('description', ''))[:200])}...</p>
            <div style="font-size: 0.8rem; margin-top: 0.4rem;">
                🔍 <a href="{recruiter_search_url}" target="_blank" style="color: #64b5f6; text-decoration: none;">Find Recruiters at {html.escape(str(row.get('company')))} ↗</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_act1, col_act2 = st.columns([2, 8])
        with col_act1:
            is_saved = jid in st.session_state["saved_ids"]
            if st.button("⭐ Saved" if is_saved else "☆ Save", key=f"btn_save_{jid}"):
                if is_saved:
                    st.session_state["saved_ids"].remove(jid)
                else:
                    st.session_state["saved_ids"].add(jid)
                st.rerun()

# ----------------- TAB 2: ATS RESUME MATCHER -----------------
with tab_ats:
    st.subheader("📄 Local ATS Matcher & Keyword Gap Analysis")
    st.caption("Calculates TF-IDF similarity and skill overlap locally without external APIs.")

    r_col1, r_col2 = st.columns(2)
    with r_col1:
        uploaded_res = st.file_uploader("Upload Resume (PDF or TXT)", type=["pdf", "txt"])
        res_text = ""
        if uploaded_res:
            res_text = extract_pdf_text(uploaded_res) if uploaded_res.type == "application/pdf" else uploaded_res.read().decode("utf-8")
            st.success(f"Resume parsed ({len(res_text.split())} words)")

    with r_col2:
        target_idx = st.selectbox(
            "Select Job to Compare",
            range(len(df)),
            format_func=lambda x: f"{df.iloc[x]['title']} @ {df.iloc[x]['company']}"
        )
        selected_job = df.iloc[target_idx]

    if st.button("🚀 Calculate Local ATS Match", type="primary"):
        if not res_text:
            st.warning("Please upload a resume first.")
        else:
            job_full_text = f"{selected_job['title']} {selected_job['description']} {' '.join(selected_job.get('skills', []))}"
            score, matched_k, missing_k = calculate_local_ats_score(res_text, job_full_text)

            st.metric("Estimated ATS Match Score", f"{score}%")
            st.progress(score / 100)

            k1, k2 = st.columns(2)
            with k1:
                st.markdown("#### ✅ Matched Keywords")
                if matched_k:
                    st.write(", ".join([f"`{k}`" for k in matched_k]))
                else:
                    st.write("No direct skill matches found.")
            with k2:
                st.markdown("#### ⚠️ Missing Keywords in Resume")
                if missing_k:
                    st.write(", ".join([f"`{k}`" for k in missing_k]))
                else:
                    st.write("Great job! All key job skills are mentioned in your resume.")

# ----------------- TAB 3: NETWORKING TEMPLATES -----------------
with tab_outreach:
    st.subheader("✉️ High-Converting LinkedIn Outreach Templates")
    
    t_role = st.selectbox("Select Target Job", range(len(df)), format_func=lambda x: f"{df.iloc[x]['title']} @ {df.iloc[x]['company']}", key="tpl_job")
    job_item = df.iloc[t_role]
    
    my_name = st.text_input("Your Name", "Candidate")
    template_type = st.radio("Template Purpose", ["Connection Request (<300 chars)", "Hiring Manager InMail", "Follow-up After Applying"])

    if template_type == "Connection Request (<300 chars)":
        msg = f"Hi {{Recruiter Name}}, I noticed the {job_item['title']} opening at {job_item['company']}. With experience in {', '.join(job_item['skills'][:2])}, I'd love to connect and follow {job_item['company']}'s work. Best, {my_name}"
    elif template_type == "Hiring Manager InMail":
        msg = f"Subject: Application for {job_item['title']} - {my_name}\n\nHi {{Hiring Manager Name}},\n\nI recently applied for the {job_item['title']} position at {job_item['company']}. Given my background in {', '.join(job_item['skills'][:3])}, I am confident I can contribute to your team's upcoming milestones.\n\nI would welcome the opportunity to discuss how my skill set aligns with your current priorities.\n\nBest regards,\n{my_name}"
    else:
        msg = f"Subject: Following up: {job_item['title']} application\n\nHi {{Contact Name}},\n\nI wanted to follow up on my application for the {job_item['title']} role at {job_item['company']}. I remain very enthusiastic about the opportunity to join your team.\n\nPlease let me know if any additional information is needed.\n\nThanks,\n{my_name}"

    st.code(msg, language="markdown")

# ----------------- TAB 4: MARKET INSIGHTS -----------------
with tab_charts:
    st.subheader("📊 Job Market Intelligence")
    ch1, ch2 = st.columns(2)
    
    with ch1:
        all_skills = [s for sub in df["skills"] if isinstance(sub, list) for s in sub]
        if all_skills:
            top_skills = pd.Series(all_skills).value_counts().head(10).reset_index()
            top_skills.columns = ["Skill", "Count"]
            fig_skills = px.bar(top_skills, x="Count", y="Skill", orientation="h", title="Top In-Demand Skills", color="Count", color_continuous_scale="Blues")
            st.plotly_chart(fig_skills, use_container_width=True)

    with ch2:
        top_companies = df["company"].value_counts().head(10).reset_index()
        top_companies.columns = ["Company", "Openings"]
        fig_comp = px.pie(top_companies, names="Company", values="Openings", title="Openings by Top Companies", hole=0.4)
        st.plotly_chart(fig_comp, use_container_width=True)

# ----------------- TAB 5: KANBAN TRACKER -----------------
with tab_kanban:
    st.subheader("📌 Application Tracking Board")
    
    stages = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]
    selected_stage = st.selectbox("Filter by Stage", ["All"] + stages)

    for idx, row in df.iterrows():
        jid = str(row.get("id", idx))
        if jid in st.session_state["saved_ids"]:
            current_stage = st.session_state["applications"].get(jid, "Saved")
            if selected_stage == "All" or selected_stage == current_stage:
                with st.expander(f"**{row['title']}** @ *{row['company']}* — [{current_stage}]"):
                    new_stage = st.selectbox("Update Stage", stages, index=stages.index(current_stage), key=f"stage_{jid}")
                    st.session_state["applications"][jid] = new_stage
                    st.write(f"Location: {row['location']}")
                    st.write(f"[View Job Link]({row.get('link')})")
