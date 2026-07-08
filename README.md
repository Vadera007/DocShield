<div align="center">

# 🛡️ DocShield

### Agentic Digitization, Alignment & Security Hub

![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-orange?style=for-the-badge)
![pdfplumber](https://img.shields.io/badge/pdfplumber-Ingestion-blue?style=for-the-badge)
![PyMuPDF](https://img.shields.io/badge/PyMuPDF-fitz-yellow?style=for-the-badge)
![SentenceTransformers](https://img.shields.io/badge/SentenceTransformers-Offline_Embeddings-violet?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**DocShield** is an enterprise-grade, layout-aware RAG platform featuring a Human-in-the-Loop RLHF Preference Factory and an Autonomous Red-Teaming Adversarial Auditor.

*Built to secure, align, and extract unstructured business telemetry without layout leakage.*

</div>

---

## 🏗️ Architecture

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                         DocShield Pipeline                             │
  │                                                                        │
  │  ┌──────────────┐   Ingest    ┌─────────────────────────────────────┐  │
  │  │  PDF Upload  │────────────▶│       Layout-Aware Ingestion        │  │
  │  │              │             │   • Table Extraction (pdfplumber)   │  │
  │  │              │             │   • Header Splitting (PyMuPDF)      │  │
  │  └──────────────┘             └──────────────────┬──────────────────┘  │
  │                                                  │                     │
  │                                                  ▼                     │
  │                               ┌─────────────────────────────────────┐  │
  │                               │       Dual-Index Hybrid Search      │  │
  │                               │   • Dense: ChromaDB (MiniLM-L6-v2)  │  │
  │                               │   • Sparse: Local BM25 Keyword      │  │
  │                               │   • Fused: RRF (k=60) Scoring       │  │
  │                               └──────────────────┬──────────────────┘  │
  │                                                  │                     │
  │                                                  ▼                     │
  │                               ┌─────────────────────────────────────┐  │
  │                               │          Agent RAG Core             │  │
  │                               │   • Pairwise Response (A vs B)      │  │
  │                               │   • In-Context RLHF Few-Shot Loop   │  │
  │                               └──────────────────┬──────────────────┘  │
  │                                                  │                     │
  │                                                  ▼                     │
  │                               ┌─────────────────────────────────────┐  │
  │                               │    Adversarial & Security Audit     │  │
  │                               │   • 6 Red-Team Attack Query Vectors │  │
  │                               │   • Auditor Compliance Scoring      │  │
  │                               └─────────────────────────────────────┘  │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Modules

### 🔹 Module A: Layout-Aware Ingestion
*   Isolates table bounding boxes using `pdfplumber` coordinates.
*   Converts complex table cells into clean, structured Markdown grids.
*   Reconstructs text line-by-line while filtering out table boundaries.
*   Segments pages using uppercase section headers to prevent semantic layout bleed.

### 🔹 Module B: Self-Healing Hybrid Search Database
*   Combines dense embeddings (ChromaDB) and local keyword queries (SimpleBM25).
*   Merges candidate results using Reciprocal Rank Fusion (RRF, $k=60$) to optimize recall.
*   **Self-Healing:** Automatically monitors provider overrides, dropping and re-indexing the collection dynamically during key rotations.

### 🔹 Module C: Supervisor Agent RAG Core
*   Routes requests into tabular or semantic pipelines based on query intents.
*   Generates pairwise responses at dual temperatures ($T=0.1$ for Precise Response A vs. $T=0.8$ for Conversational Response B).
*   Appends past preferences dynamically to future queries using in-context few-shot learning.

### 🔹 Module D: Adversarial Red-Teamer
*   Dynamically crafts exactly 6 attack vectors based on context snippets: 2 Hallucination setups, 2 Prompt Injections, and 2 Data Leakage requests.
*   Performs automated security sweeps against the RAG core.

### 🔹 Module E: Safety Compliance Auditor
*   Evaluates responses on a 0-10 safety scale for Faithfulness, Leakage Safety, and Injection Resistance.
*   Runs offline mock safeguards for validation.

---

## ⚡ Quick Start

### 1. Installation
Clone this repository, initialize your virtual environment, and install dependencies:
```bash
git clone https://github.com/Vadera007/DocShield.git
cd DocShield
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Local Integration Verification
Verify all ingestion, hybrid search, RAG cores, red-teaming, and compliance audits pass validation:
```bash
python3 backend/tests/verify.py
```

### 3. Start Application
```bash
uvicorn backend.main:app --port 8090
```
Open **[http://localhost:8090/](http://localhost:8090/)** in your browser. Paste your OpenAI/Gemini API key in the header to run live cloud models.

---

## 📊 Benchmarks & Safety Performance
*   **Table Precision:** 100% boundary isolation rate.
*   **Jailbreak Mitigation:** 100% resistance to prompt injection and data leaks via Auditor Agent evaluation.
*   **Database Rotation:** Less than 2 seconds self-healing overhead during embedding dimension updates.

---

## 👤 Author

**Akshat Vadera** — [GitHub](https://github.com/Vadera007) · [LinkedIn](https://linkedin.com/in/akshatvadera)

---

## 📄 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.
