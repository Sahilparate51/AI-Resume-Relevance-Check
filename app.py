import streamlit as st
import os
import pandas as pd
import altair as alt
from fpdf import FPDF
from extractor import extract_text
from matcher import hard_match_score, semantic_match_score, calculate_final_score, get_verdict, generate_llm_feedback
from database import create_table, insert_evaluation, fetch_all_evaluations

# ----------------- PAGE CONFIG -----------------
st.set_page_config(page_title="AI Resume Relevance Check", layout="wide")

# Initialize database
create_table()

# ----------------- CUSTOM CSS -----------------
st.markdown("""
<style>
    .stApp {
        background-color: #0e1a2b;
        color: #f8f9fa;
        font-family: 'Segoe UI', Roboto, Arial, sans-serif;
    }
    h1, h2, h3, h4, h5, h6, .stMarkdown {
        color: #f8f9fa;
    }
    .stButton>button {
        background: linear-gradient(90deg, #4CAF50 0%, #2e7d32 100%);
        color: white;
        border-radius: 12px;
        padding: 12px 28px;
        border: none;
        font-weight: bold;
        font-size: 16px;
        transition: 0.3s;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #45a049 0%, #1b5e20 100%);
        transform: scale(1.05);
    }
    .stExpander, .stDataFrame, .stMetric > div {
        background-color: #182c47;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.4);
    }
    .stExpander, .stDataFrame {
        border: 1px solid #2d3f5e;
    }
    .stMetric > div {
        border: 1px solid #2d3f5e;
    }
    .stFileUploader > div > div > button {
        background-color: #2e3a59;
        color: white;
    }
    .block-container {
        padding-top: 2rem;
    }
    .download-btn {
        text-align: center;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE -----------------
if 'jd_text' not in st.session_state:
    st.session_state['jd_text'] = ""
if 'analysis_results' not in st.session_state:
    st.session_state['analysis_results'] = []
if 'jd_filename' not in st.session_state:
    st.session_state['jd_filename'] = ""

# ----------------- HEADER -----------------
st.markdown(
    "<h1 style='text-align:center; color:#4CAF50;'>✨ AI-Powered Resume Relevance Check ✨</h1>",
    unsafe_allow_html=True
)
st.markdown("<hr>", unsafe_allow_html=True)

# ----------------- 1. Upload Job Description -----------------
st.header("📄 1. Upload Job Description (JD)")
jd_file = st.file_uploader("Choose a PDF or DOCX file...", type=["pdf", "docx"], key="jd_uploader")

if jd_file:
    with st.spinner("Processing JD..."):
        jd_path = os.path.join("temp", jd_file.name)
        os.makedirs("temp", exist_ok=True)
        with open(jd_path, "wb") as f:
            f.write(jd_file.getbuffer())

        st.session_state['jd_text'] = extract_text(jd_path)
        st.session_state['jd_filename'] = jd_file.name

    if "Error" in st.session_state['jd_text']:
        st.error(f"Failed to process JD: {st.session_state['jd_text']}")
    else:
        st.success("✅ JD uploaded and parsed successfully!")

st.markdown("<hr>", unsafe_allow_html=True)

# ----------------- 2. Upload Resumes -----------------
st.header("📂 2. Upload Resumes")
resume_files = st.file_uploader(
    "Choose one or more resume files...",
    type=["pdf", "docx"],
    accept_multiple_files=True,
    key="resume_uploader"
)

if st.button("🚀 Analyze Resumes", use_container_width=True):
    if not st.session_state['jd_text']:
        st.error("⚠️ Please upload a Job Description first.")
    elif not resume_files:
        st.warning("⚠️ Please upload at least one resume.")
    else:
        st.session_state['analysis_results'] = []
        with st.spinner("🔎 Analyzing resumes..."):
            progress_bar = st.progress(0)

            for i, resume_file in enumerate(resume_files):
                progress_bar.progress((i + 1) / len(resume_files))

                resume_path = os.path.join("temp", resume_file.name)
                with open(resume_path, "wb") as f:
                    f.write(resume_file.getbuffer())
                resume_text = extract_text(resume_path)

                if "Error" in resume_text or "Unsupported" in resume_text:
                    st.session_state['analysis_results'].append({
                        'Resume Filename': resume_file.name,
                        'Verdict': 'Processing Error',
                        'Score': 0,
                        'Feedback': f"❌ Failed to process resume: {resume_text}"
                    })
                    continue

                hard_score, missing_skills = hard_match_score(resume_text, st.session_state['jd_text'])
                semantic_score = semantic_match_score(resume_text, st.session_state['jd_text'])
                final_score = calculate_final_score(hard_score, semantic_score)
                verdict = get_verdict(final_score)

                feedback = generate_llm_feedback(resume_text, st.session_state['jd_text'], verdict, missing_skills)

                insert_evaluation(
                    st.session_state['jd_filename'], resume_file.name,
                    final_score, verdict, ", ".join(missing_skills), feedback
                )

                st.session_state['analysis_results'].append({
                    'JD Title': st.session_state['jd_filename'],
                    'Resume Filename': resume_file.name,
                    'Score': final_score,
                    'Hard Score': hard_score,
                    'Semantic Score': semantic_score,
                    'Verdict': verdict,
                    'Missing Skills': ", ".join(missing_skills),
                    'Feedback': feedback
                })

        st.balloons()
        st.success("🎉 Analysis complete!")

st.markdown("<hr>", unsafe_allow_html=True)

# ----------------- 3. Analysis Results -----------------
st.header("📊 3. Analysis Results")

def create_pdf(feedback_text, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in feedback_text.split("\n"):
        pdf.multi_cell(0, 8, line)
    pdf_path = os.path.join("temp", filename)
    pdf.output(pdf_path)
    return pdf_path

if st.session_state['analysis_results']:
    for result in st.session_state['analysis_results']:
        st.subheader(f"📌 Results for: `{result['Resume Filename']}`")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Relevance Score", f"{result['Score']:.2f} / 100")
        with col2:
            if result['Verdict'] == "High suitability":
                st.success(f"✅ Verdict: {result['Verdict']}")
            elif result['Verdict'] == "Medium suitability":
                st.warning(f"⚠️ Verdict: {result['Verdict']}")
            else:
                st.error(f"❌ Verdict: {result['Verdict']}")

        with st.expander("📖 Show Detailed Report", expanded=True):
            chart_col1, chart_col2 = st.columns(2)

            # Bar Chart (Hard vs Semantic)
            with chart_col1:
                st.subheader("📊 Skills Match Breakdown")
                skills_data = pd.DataFrame({
                    'Metric': ['Hard Match Score', 'Semantic Match Score'],
                    'Score': [result['Hard Score'], result['Semantic Score']]
                })

                bar_chart = (
                    alt.Chart(skills_data)
                    .mark_bar(cornerRadiusTopLeft=10, cornerRadiusTopRight=10)
                    .encode(
                        x=alt.X('Metric', sort=None, axis=alt.Axis(labelAngle=0, title="Metric")),
                        y=alt.Y('Score', title='Score'),
                        color=alt.Color(
                            'Metric',
                            scale=alt.Scale(range=['#4CAF50', '#2196F3']),
                            legend=alt.Legend(title="Legend", labelFontSize=14, titleFontSize=16)
                        ),
                        tooltip=['Metric', 'Score']
                    )
                )
                st.altair_chart(bar_chart, use_container_width=True)

            # Donut Chart (Overall Score)
            with chart_col2:
                st.subheader("🏆 Overall Relevance Score")
                final_score = result['Score']
                score_chart_data = pd.DataFrame({
                    'Category': ['Relevance Score', 'Remaining'],
                    'Value': [final_score, 100 - final_score]
                })

                base = alt.Chart(score_chart_data).encode(
                    theta=alt.Theta("Value", stack=True),
                    color=alt.Color(
                        "Category",
                        scale=alt.Scale(range=['#4CAF50', '#2e3a59']),
                        legend=alt.Legend(title="Legend", labelFontSize=14, titleFontSize=16)
                    )
                )

                pie = base.mark_arc(outerRadius=120, innerRadius=80)
                text = alt.Chart(pd.DataFrame({'text': [f"{final_score:.0f}%"]})).mark_text(
                    size=28, color="#f0f4f8", fontWeight="bold"
                ).encode(text="text")

                st.altair_chart(pie + text, use_container_width=True)

            st.markdown(f"**🛠 Missing Skills:** `{result['Missing Skills'] if result['Missing Skills'] else 'None'}`")
            st.markdown(f"**💡 Personalized Feedback:** {result['Feedback']}")

            # ----------------- Improved Download PDF Button -----------------
            feedback_text = f"Resume: {result['Resume Filename']}\nJD: {st.session_state['jd_filename']}\nScore: {result['Score']:.2f}\nVerdict: {result['Verdict']}\nMissing Skills: {result['Missing Skills']}\nFeedback: {result['Feedback']}"
            pdf_filename = f"{result['Resume Filename'].split('.')[0]}_feedback.pdf"
            pdf_path = create_pdf(feedback_text, pdf_filename)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download Feedback PDF",
                    data=f,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    key=f"download_{result['Resume Filename']}",
                    use_container_width=True
                )

        st.write("---")
else:
    st.info("ℹ️ Upload a JD and resumes, then click **Analyze** to see results.")

st.markdown("<hr>", unsafe_allow_html=True)

# ----------------- 4. Placement Team Dashboard -----------------
st.header("📋 4. Placement Team Dashboard")
evaluations = fetch_all_evaluations()
if evaluations:
    df = pd.DataFrame(
        evaluations,
        columns=['ID', 'JD Title', 'Resume Filename', 'Score', 'Verdict', 'Missing Skills', 'Feedback', 'Timestamp']
    )
    df['Score'] = df['Score'].round(2)
    st.dataframe(df)
else:
    st.info("📭 No evaluations found yet. Upload a JD and resumes to get started.")
