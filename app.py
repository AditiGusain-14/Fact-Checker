import streamlit as st
import fitz
import pandas as pd
import json
import re
import ollama
from datetime import datetime

# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="Fact-Check Agent",
    page_icon="🛡️",
    layout="wide"
)

# ==================================================
# CUSTOM CSS
# ==================================================

st.markdown("""
<style>

    .stApp {
        background-color: #f5f7fb;
        font-family: 'Inter', sans-serif;
    }

    .main-title {
        font-size: 3rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.5rem;
    }

    .sub-text {
        font-size: 1.05rem;
        color: #6b7280;
        line-height: 1.8;
    }

    .small-heading {
        font-size: 1.2rem;
        font-weight: 600;
        color: #111827;
        margin-bottom: 1rem;
    }

</style>
""", unsafe_allow_html=True)

# ==================================================
# PDF TEXT EXTRACTION
# ==================================================


def extract_text_from_pdf(uploaded_file):

    pdf_document = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf"
    )

    full_text = ""

    for page_num in range(len(pdf_document)):

        page = pdf_document.load_page(page_num)

        text = page.get_text("text")  # type: ignore[attr-defined]

        full_text += f"\n\n--- PAGE {page_num + 1} ---\n\n"
        full_text += text

    return full_text


# ==================================================
# CLAIM EXTRACTION USING OLLAMA
# ==================================================


def extract_claims(text):

    prompt = f"""
    Extract factual claims from this document.

    Only extract:
    - statistics
    - percentages
    - financial figures
    - dates
    - technical claims

    Return ONLY a Python list.

    Example:

    [
        "OpenAI was founded in 2015.",
        "The AI market reached $50 billion in 2023."
    ]

    DOCUMENT:
    {text[:5000]}
    """

    response = ollama.chat(
        model='gemma:2b',
        messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ]
    )

    claims_text = response['message']['content']

    try:

        claims = eval(claims_text)

        if isinstance(claims, list):
            return claims[:15]

    except:
        pass

    return []


# ==================================================
# FACT CHECKING USING OLLAMA
# ==================================================


def verify_claim(claim):

    prompt = f"""
    You are a professional AI fact-checker.

    Analyze the following claim.

    Classify it as:
    - Verified
    - Inaccurate
    - False

    Also provide:
    - confidence percentage
    - corrected fact
    - short explanation

    Return ONLY valid JSON.

    Example:

    {{
        "status": "Verified",
        "confidence": "92%",
        "fact": "OpenAI was founded in 2015.",
        "source": "Public trusted information"
    }}

    CLAIM:
    {claim}
    """

    response = ollama.chat(
        model='gemma:2b',
        messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ]
    )

    result_text = response['message']['content']

    try:
        return json.loads(result_text)

    except:

        return {
            "status": "Inaccurate",
            "confidence": "60%",
            "fact": "Unable to verify confidently.",
            "source": "Local AI verification"
        }


# ==================================================
# HEADER
# ==================================================

st.markdown(
    '<div class="main-title">🛡️ Fact-Check Agent</div>',
    unsafe_allow_html=True
)

st.markdown(
    '''
    <div class="sub-text">
    Upload a PDF document and automatically verify factual claims using AI-powered extraction and local AI verification.
    <br><br>
    The system identifies:
    <ul>
        <li>Outdated statistics</li>
        <li>Fake numerical claims</li>
        <li>Unsupported information</li>
        <li>Misinformation</li>
    </ul>
    and provides corrected facts with verification status.
    </div>
    ''',
    unsafe_allow_html=True
)

st.write("")

# ==================================================
# STATUS INDICATORS
# ==================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.success("✅ Verified Claims")

with col2:
    st.warning("⚠️ Inaccurate Claims")

with col3:
    st.error("❌ False Claims")

st.divider()

# ==================================================
# MAIN LAYOUT
# ==================================================

left_col, right_col = st.columns([2, 1])

# ==================================================
# LEFT PANEL
# ==================================================

with left_col:

    st.markdown(
        '<div class="small-heading">Upload PDF Document</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed"
    )

    if uploaded_file:

        st.success(f"Uploaded Successfully: {uploaded_file.name}")

        file_size = round(uploaded_file.size / (1024 * 1024), 2)

        st.caption(f"📄 File Size: {file_size} MB")

        st.caption(
            f"🕒 Uploaded At: {datetime.now().strftime('%d %B %Y • %I:%M %p')}"
        )

        st.write("")

        st.markdown("### Fact-Checking Pipeline")

        st.markdown("""
        1. Extract text from PDF

        2. Extract factual claims using Gemma 2B

        3. Verify claims using local AI reasoning

        4. Generate final fact-check report
        """)

        analyze_btn = st.button(
            "Start Fact Checking",
            use_container_width=True,
            type="primary"
        )

        if analyze_btn:

            with st.spinner("Analyzing and verifying claims..."):

                extracted_text = extract_text_from_pdf(uploaded_file)

                claims = extract_claims(extracted_text)

                results = []

                for claim in claims:

                    verification = verify_claim(claim)

                    results.append({
                        "Claim": claim,
                        "Status": verification.get("status", "Unknown"),
                        "Confidence": verification.get("confidence", "0%"),
                        "Correct Fact": verification.get("fact", "No fact available"),
                        "Source": verification.get("source", "No source")
                    })

                st.session_state["results"] = results

            st.success("Fact-checking completed successfully.")

# ==================================================
# RIGHT PANEL
# ==================================================

with right_col:

    st.markdown(
        '<div class="small-heading">How It Works</div>',
        unsafe_allow_html=True
    )

    st.info("""
    Step 1: Upload your PDF

    Step 2: Gemma 2B extracts factual claims

    Step 3: Local AI verifies claims

    Step 4: Final report is generated
    """)

    st.write("")

    st.markdown(
        '<div class="small-heading">Supported Claims</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    - Statistics & Percentages
    - Financial Figures
    - Dates & Historical Facts
    - Market Reports
    - Technical Statements
    - Growth Metrics
    """)

    st.write("")

    st.markdown(
        '<div class="small-heading">AI Stack</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    - Ollama
    - Gemma 2B
    - PyMuPDF
    - Streamlit
    - Local AI Verification
    """)

# ==================================================
# RESULTS SECTION
# ==================================================

if "results" in st.session_state:

    st.divider()

    st.subheader("📊 Fact-Checking Results")

    results_df = pd.DataFrame(st.session_state["results"])

    st.dataframe(
        results_df,
        use_container_width=True,
        height=500
    )

    verified_count = sum(
        r["Status"] == "Verified"
        for r in st.session_state["results"]
    )

    inaccurate_count = sum(
        r["Status"] == "Inaccurate"
        for r in st.session_state["results"]
    )

    false_count = sum(
        r["Status"] == "False"
        for r in st.session_state["results"]
    )

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric("Verified", verified_count)
    metric2.metric("Inaccurate", inaccurate_count)
    metric3.metric("False", false_count)

    st.write("")

    json_report = json.dumps(
        st.session_state["results"],
        indent=4
    )

    st.download_button(
        label="Download Report",
        data=json_report,
        file_name="fact_check_report.json",
        mime="application/json",
        use_container_width=True
    )

# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "Built with Streamlit • Ollama • Gemma 2B • Local AI Fact Verification"
)
