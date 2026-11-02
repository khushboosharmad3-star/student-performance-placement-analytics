import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Student Performance & Placement Analytics", page_icon="🎓", layout="wide")

REQUIRED_COLUMNS = [
    "student_id", "specialisation", "attendance", "academic_score",
    "placement_status", "salary_lpa"
]

@st.cache_data
def load_sample():
    return pd.read_csv(Path(__file__).parent / "sample_data.csv")

def prepare_data(df):
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    for col in ["attendance", "academic_score", "salary_lpa"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["placement_status"] = df["placement_status"].astype(str).str.strip().str.title()
    df["specialisation"] = df["specialisation"].astype(str).str.strip()
    df["grade"] = pd.cut(
        df["academic_score"],
        bins=[-1, 49, 59, 69, 79, 100],
        labels=["F", "D", "C", "B", "A"]
    )
    df["performance_band"] = df.apply(
        lambda r: "Excellent" if r["academic_score"] >= 80 and r["attendance"] >= 85
        else ("Good" if r["academic_score"] >= 70 and r["attendance"] >= 75
        else ("Average" if r["academic_score"] >= 60 and r["attendance"] >= 65
        else "Needs Improvement")), axis=1
    )
    return df

def recommendations(row):
    tips = []
    if pd.notna(row["academic_score"]) and row["academic_score"] < 60:
        tips.append("Arrange subject-wise tutoring and weekly assessments.")
    elif pd.notna(row["academic_score"]) and row["academic_score"] < 70:
        tips.append("Provide targeted revision and practice assignments.")
    if pd.notna(row["attendance"]) and row["attendance"] < 75:
        tips.append("Schedule an attendance review and mentoring check-in.")
    if row["placement_status"] != "Placed":
        tips.append("Offer CV support, aptitude practice and mock interviews.")
    if not tips:
        tips.append("Maintain performance; consider advanced projects and placement preparation.")
    return " ".join(tips)

st.title("🎓 Student Performance & Placement Analytics")
st.caption("Explore academic performance, attendance, specialisations and placement outcomes.")

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload student data (CSV)", type=["csv"])
    st.caption("No file? The app starts with the included sample dataset.")
    if uploaded:
        try:
            raw = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            st.stop()
    else:
        raw = load_sample()

try:
    data = prepare_data(raw)
except Exception as e:
    st.error(str(e))
    st.info("Required columns: " + ", ".join(REQUIRED_COLUMNS))
    st.stop()

if data.empty:
    st.warning("The dataset has no student records.")
    st.stop()

with st.sidebar:
    st.divider()
    specialisations = sorted(data["specialisation"].dropna().unique().tolist())
    selected_specs = st.multiselect("Filter specialisation", specialisations, default=specialisations)
    placement_filter = st.selectbox("Placement status", ["All", "Placed", "Not Placed"])

filtered = data[data["specialisation"].isin(selected_specs)].copy()
if placement_filter == "Placed":
    filtered = filtered[filtered["placement_status"] == "Placed"]
elif placement_filter == "Not Placed":
    filtered = filtered[filtered["placement_status"] != "Placed"]

total = len(filtered)
placed = int((filtered["placement_status"] == "Placed").sum())
placement_rate = (placed / total * 100) if total else 0
avg_score = filtered["academic_score"].mean()
avg_attendance = filtered["attendance"].mean()
placed_salary = filtered.loc[filtered["placement_status"] == "Placed", "salary_lpa"].dropna()
avg_salary = placed_salary.mean()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Students", f"{total:,}")
k2.metric("Placed", f"{placed:,}")
k3.metric("Placement rate", f"{placement_rate:.1f}%")
k4.metric("Average score", f"{avg_score:.1f}" if pd.notna(avg_score) else "N/A")
k5.metric("Average salary", f"₹{avg_salary:.2f} LPA" if pd.notna(avg_salary) else "N/A")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📚 Academic analysis", "💼 Placement analysis", "🧭 Student interventions"])

with tab1:
    left, right = st.columns(2)
    with left:
        grade_counts = filtered["grade"].value_counts().reindex(["A", "B", "C", "D", "F"]).fillna(0).reset_index()
        grade_counts.columns = ["Grade", "Students"]
        st.subheader("Grade distribution")
        st.plotly_chart(px.bar(grade_counts, x="Grade", y="Students", color="Grade"), use_container_width=True)
    with right:
        status_counts = filtered["placement_status"].value_counts().rename_axis("Status").reset_index(name="Students")
        st.subheader("Placement status")
        st.plotly_chart(px.pie(status_counts, names="Status", values="Students", hole=0.45), use_container_width=True)

    st.subheader("Student records")
    st.dataframe(filtered, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Academic score and attendance")
    st.plotly_chart(
        px.scatter(filtered, x="attendance", y="academic_score", color="performance_band",
                   hover_data=["student_id", "specialisation"], trendline="ols",
                   labels={"attendance": "Attendance (%)", "academic_score": "Academic score"}),
        use_container_width=True
    )
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Average score by specialisation")
        by_spec = filtered.groupby("specialisation", as_index=False)["academic_score"].mean()
        st.plotly_chart(px.bar(by_spec, x="specialisation", y="academic_score"), use_container_width=True)
    with c2:
        st.subheader("Performance bands")
        band = filtered["performance_band"].value_counts().rename_axis("Band").reset_index(name="Students")
        st.plotly_chart(px.bar(band, x="Band", y="Students", color="Band"), use_container_width=True)

with tab3:
    st.subheader("Placement outcomes by specialisation")
    placement_by_spec = filtered.assign(placed=(filtered["placement_status"] == "Placed").astype(int)).groupby(
        "specialisation", as_index=False
    ).agg(students=("student_id", "count"), placement_rate=("placed", "mean"))
    placement_by_spec["placement_rate"] *= 100
    st.plotly_chart(px.bar(placement_by_spec, x="specialisation", y="placement_rate",
                           labels={"placement_rate": "Placement rate (%)"}), use_container_width=True)

    placed_rows = filtered[(filtered["placement_status"] == "Placed") & filtered["salary_lpa"].notna()]
    if len(placed_rows) >= 2:
        st.subheader("Academic score vs placement salary")
        corr = placed_rows["academic_score"].corr(placed_rows["salary_lpa"])
        st.metric("Correlation (score and salary)", f"{corr:.2f}" if pd.notna(corr) else "N/A",
                  help="Pearson correlation ranges from -1 to +1. Correlation does not prove causation.")
        st.plotly_chart(px.scatter(placed_rows, x="academic_score", y="salary_lpa",
                                   color="specialisation", hover_data=["student_id"],
                                   labels={"academic_score": "Academic score", "salary_lpa": "Salary (LPA)"}),
                        use_container_width=True)
    else:
        st.info("At least two placed students with salary data are needed for salary correlation.")

with tab4:
    st.subheader("Recommended interventions")
    intervention_data = filtered.copy()
    intervention_data["recommendation"] = intervention_data.apply(recommendations, axis=1)
    priority = intervention_data[
        (intervention_data["performance_band"] == "Needs Improvement") |
        (intervention_data["placement_status"] != "Placed")
    ].copy()
    st.write(f"Students who may benefit from additional support: **{len(priority)}**")
    st.dataframe(priority[["student_id", "specialisation", "academic_score", "attendance",
                           "grade", "performance_band", "placement_status", "recommendation"]],
                 use_container_width=True, hide_index=True)
    csv_bytes = intervention_data.to_csv(index=False).encode("utf-8")
    st.download_button("Download analyzed student data (CSV)", csv_bytes,
                       file_name="analyzed_student_data.csv", mime="text/csv")

st.divider()
st.caption("Academic grades and intervention rules are example rules for this project. Adapt them to your institution's official policy.")
