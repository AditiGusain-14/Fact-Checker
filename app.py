import streamlit as st
import fitz
import pandas as pd
import json
import re
import requests
from duckduckgo_search import DDGS
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
# HUGGING FACE CONFIG
# ==================================================

HF_TOKEN = st.secrets["HF_TOKEN"]

API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"

headers = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

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
}

.sub-text {
    color: #6b7280;
    font-size: 1.05rem;
    line-height: 1.8;
}

.small-heading {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 1rem;
}

</style>
""", unsafe_allow_html=True)

# ==================================================
# HUGGING FACE QUERY
# ==================================================

def query_huggingface(prompt):

    payload = {
        "inputs": prompt
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    try:

        output = response.json()

        if isinstance(output, list):

            return output[0]["generated_text"]

        return str(output)

    except:

        return ""

# ==================================================
# PDF EXTRACTION
# ==================================================

def extract_text_from_pdf(uploaded_file):

    pdf_document = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf"
    )

    full_text = ""

    for page_num in range(len(pdf_document)):

        page = pdf_document.load_page(page_num)

        text = page.get_text("text")  # type: ignore

        full_text += text

    return full_text

# ==================================================
# CLAIM EXTRACTION
# ==================================================

def extract_claims(text):

    claims = []

    sentences = re.split(r'(?<=[.!?])\s+', text)

    patterns = [
        r'\d+%',
        r'\$\d+',
        r'\d{4}',
        r'\d+\s?(million|billion|trillion)',
        r'\d+\.\d+'
    ]

    for sentence in sentences:

        for pattern in patterns:

            if re.search(pattern, sentence, re.IGNORECASE):

                claims.append(sentence.strip())

                break

    unique_claims = list(set(claims))

    return unique_claims[:10]

# ==================================================
# LIVE WEB SEARCH
# ==================================================

def search_web(claim):

    try:

        with DDGS() as ddgs:

            results = list(
                ddgs.text(
                    claim,
                    max_results=5
                )
            )

        snippets = []

        for result in results:

            snippets.append(
                result.get("body", "")
            )

        return " ".join(snippets)

    except:

        return ""

# ==================================================
# KEYWORD OVERLAP SCORE
# Measures how many meaningful words from the claim
# appear in the web evidence (0.0 to 1.0)
# ==================================================

def keyword_overlap_score(claim, evidence):

    if not evidence:
        return 0.0

    stopwords = {
        "the", "a", "an", "in", "of", "and", "to", "is",
        "was", "were", "it", "that", "for", "on", "at",
        "by", "with", "from", "has", "have", "had", "be",
        "its", "are", "this", "as", "or", "but", "not"
    }

    claim_words = set(
        w.lower()
        for w in re.findall(r'\b\w+\b', claim)
        if w.lower() not in stopwords and len(w) > 2
    )

    evidence_words = set(
        w.lower()
        for w in re.findall(r'\b\w+\b', evidence)
    )

    if not claim_words:
        return 0.0

    overlap = claim_words & evidence_words

    return len(overlap) / len(claim_words)

# ==================================================
# CONTRADICTION DETECTION
# Looks for explicit contradicting numbers/years in
# the evidence that differ from the claim's values
# ==================================================

def detect_contradiction(claim, evidence):

    if not evidence:
        return False

    # Extract years from claim
    claim_years = re.findall(r'\b((?:19|20)\d{2})\b', claim)

    # Extract large numbers (millions/billions) from claim
    claim_magnitudes = re.findall(
        r'\$?([\d,]+(?:\.\d+)?)\s*(million|billion|trillion)',
        claim, re.IGNORECASE
    )

    # Extract plain percentages from claim
    claim_pcts = re.findall(r'(\d+(?:\.\d+)?)%', claim)

    # --- Year contradiction ---
    for year in claim_years:

        ev_years = re.findall(r'\b((?:19|20)\d{2})\b', evidence)

        if ev_years and year not in ev_years:
            return True

    # --- Magnitude contradiction ---
    for value, unit in claim_magnitudes:

        value_clean = value.replace(",", "")

        pattern = rf'([\d,]+(?:\.\d+)?)\s*{unit}'
        ev_magnitudes = re.findall(pattern, evidence.lower(), re.IGNORECASE)

        if ev_magnitudes:

            ev_values = [float(v.replace(",", "")) for v in ev_magnitudes]
            claim_val = float(value_clean)

            all_differ = all(
                abs(ev - claim_val) / max(claim_val, 1) > 0.20
                for ev in ev_values
            )

            if all_differ:
                return True

    # --- Percentage contradiction ---
    for pct in claim_pcts:

        ev_pcts = re.findall(r'(\d+(?:\.\d+)?)%', evidence)

        if ev_pcts:

            ev_floats = [float(p) for p in ev_pcts]
            claim_float = float(pct)

            all_differ = all(
                abs(ev - claim_float) / max(claim_float, 1) > 0.20
                for ev in ev_floats
            )

            if all_differ:
                return True

    return False

# ==================================================
# CLAIM CLEANER
# Strips label prefixes that leak into extracted
# claims and pollute search queries
# ==================================================

def clean_claim(claim):

    prefixes = [
        "Verified",
        "False",
        "Inaccurate",
        "Financial",
        "Statistical",
        "Type",
        "Claim"
    ]

    cleaned = claim

    for prefix in prefixes:

        cleaned = cleaned.replace(prefix, "")

    return cleaned.strip()

# ==================================================
# FACT CHECKING
# ==================================================

def verify_claim(claim):

    web_evidence = search_web(claim)

    # --------------------------------------------------
    # CLASSIFICATION LOGIC
    #
    # 1. No evidence returned            → False / Low
    # 2. Evidence contradicts numbers
    #    or years in the claim           → False / High
    # 3. Evidence found, no contradiction,
    #    good keyword overlap (>= 0.45)  → Verified / High
    # 4. Some overlap but not enough
    #    to fully confirm (0.20–0.44)    → Inaccurate / Medium
    # 5. Very low overlap (< 0.20)       → False / Low
    # --------------------------------------------------

    if not web_evidence.strip():

        status     = "False"
        confidence = "Low"

    else:

        contradiction = detect_contradiction(claim, web_evidence)
        overlap       = keyword_overlap_score(claim, web_evidence)

        if contradiction:

            status     = "False"
            confidence = "High"

        elif overlap >= 0.45:

            status     = "Verified"
            confidence = "High"

        elif overlap >= 0.20:

            status     = "Inaccurate"
            confidence = "Medium"

        else:

            status     = "False"
            confidence = "Low"

    # ==============================================
    # GENERATE CORRECT FACT FROM WEB EVIDENCE
    # Pull the first substantive sentence directly
    # from evidence — no model formatting required
    # ==============================================

    evidence_sentences = re.split(
        r'(?<=[.!?])\s+',
        web_evidence
    )

    correct_fact = ""

    for sentence in evidence_sentences:

        if len(sentence.strip()) > 40:

            correct_fact = sentence.strip()

            break

    if not correct_fact:

        correct_fact = web_evidence[:200]

    # ==============================================
    # AI EXPLANATION
    # Model only generates a short explanation —
    # no structured formatting required
    # ==============================================

    prompt = f"""
Explain briefly why this claim is {status}.
CLAIM:
{claim}
CORRECT FACT:
{correct_fact}
Keep explanation under 2 sentences.
"""

    reason = query_huggingface(prompt)

    source_preview = "DuckDuckGo Live Search"

    return {
        "status":     status,
        "confidence": confidence,
        "fact":       correct_fact,
        "reason":     reason,
        "source":     source_preview
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
    Upload a PDF document and automatically verify factual claims using live web evidence and AI reasoning.
    <br><br>
    The system:
    <ul>
        <li>Extracts statistical and factual claims</li>
        <li>Searches live web sources</li>
        <li>Compares claim vs evidence</li>
        <li>Detects contradictions automatically</li>
        <li>Provides corrected factual information</li>
    </ul>
    </div>
    ''',
    unsafe_allow_html=True
)

st.write("")

# ==================================================
# STATUS CARDS
# ==================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.success("✅ Verified")

with col2:
    st.warning("⚠️ Inaccurate")

with col3:
    st.error("❌ False")

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

        2. Detect factual/statistical claims

        3. Search live web evidence

        4. Compare claims vs evidence

        5. Detect contradictions

        6. Generate AI explanations
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

                    claim = clean_claim(claim)

                    verification = verify_claim(claim)

                    results.append({
                        "Claim":        claim,
                        "Status":       verification["status"],
                        "Confidence":   verification["confidence"],
                        "Correct Fact": verification["fact"],
                        "Source":       verification["source"]
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
    Step 1: Upload PDF

    Step 2: Extract Claims

    Step 3: Search Live Web

    Step 4: Compare Facts

    Step 5: AI Explanation

    Step 6: Generate Report
    """)

    st.write("")

    st.markdown(
        '<div class="small-heading">AI Stack</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    - Hugging Face API
    - DuckDuckGo Search
    - Flan-T5-Large
    - PyMuPDF
    - Streamlit
    """)

# ==================================================
# RESULTS
# ==================================================

if "results" in st.session_state:

    st.divider()

    st.subheader("📊 Fact-Checking Results")

    results_df = pd.DataFrame(
        st.session_state["results"]
    )

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

    col1, col2, col3 = st.columns(3)

    col1.metric("Verified", verified_count)
    col2.metric("Inaccurate", inaccurate_count)
    col3.metric("False", false_count)

    st.write("")

    report_json = json.dumps(
        st.session_state["results"],
        indent=4
    )

    st.download_button(
        label="Download Report",
        data=report_json,
        file_name="fact_check_report.json",
        mime="application/json",
        use_container_width=True
    )

# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "Built with Streamlit • Hugging Face • DuckDuckGo • AI Fact Verification"
)