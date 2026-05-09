# 🛡️ Fact-Check Agent

An AI-powered web application that automatically verifies factual claims from uploaded PDF documents using live web evidence and AI reasoning.

The system extracts claims containing:

* statistics
* financial figures
* percentages
* dates
* measurable statements

and verifies them against live web information.

---

# 🚀 Features

✅ Upload PDF documents
✅ Extract factual/statistical claims
✅ Live web verification using DuckDuckGo
✅ AI-powered reasoning using Hugging Face
✅ Detect false or outdated information
✅ Generate corrected factual outputs
✅ Downloadable verification reports
✅ Clean Streamlit UI
✅ Fully deployable on Streamlit Cloud

---

# 🧠 How It Works

```text
PDF Upload
   ↓
Text Extraction (PyMuPDF)
   ↓
Claim Detection
   ↓
Live Web Retrieval (DuckDuckGo)
   ↓
Contradiction Detection
   ↓
AI Reasoning (Hugging Face)
   ↓
Verification Report
```

---

# 📊 Verification Categories

| Status        | Meaning                                 |
| ------------- | --------------------------------------- |
| ✅ Verified    | Claim matches live web evidence         |
| ⚠️ Inaccurate | Claim is partially outdated or inflated |
| ❌ False       | Claim contradicts retrieved evidence    |

---

# 🛠️ Tech Stack

* Streamlit
* PyMuPDF
* DuckDuckGo Search
* Hugging Face Inference API
* Pandas
* Python

---

# 📂 Project Structure

```bash
Fact-Checker/
│
├── app.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

---

# ⚙️ Installation

## 1. Clone Repository

```bash
git clone https://github.com/AditiGusain-14/Fact-Checker.git
cd Fact-Checker
```

---

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Hugging Face API Setup

Create:

```bash
.streamlit/secrets.toml
```

Add:

```toml
HF_TOKEN = "your_huggingface_token"
```

Generate your token here:

[Hugging Face Tokens](https://huggingface.co/settings/tokens?utm_source=chatgpt.com)

---

# ▶️ Run Application

```bash
streamlit run app.py
```

---

# ☁️ Deployment

The application is fully compatible with:

* Streamlit Community Cloud
* Render
* Railway

---

# 📌 Example Claims

### Verified

* Python was first released in 1991.
* The iPhone was launched in 2007.

### Inaccurate

* Global AI market reached $500 billion in 2020.

### False

* Google was founded in 1898.

---

# 📄 Output Report

The system generates:

* claim classification
* corrected factual information
* confidence level
* evidence source

and allows report download in JSON format.

---

# ⚠️ Limitations

* Web evidence quality depends on search results.
* Complex semantic claims may require stronger reasoning models.
* Current implementation focuses primarily on numerical and factual contradictions.

---

# 👩‍💻 Author

Built as an AI-powered automated fact-checking system using live web verification and retrieval-based reasoning.
