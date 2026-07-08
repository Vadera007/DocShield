# DocShield: Agentic Digitization, Alignment & Security Hub

DocShield is a layout-aware, secure, and aligned RAG (Retrieval-Augmented Generation) platform. It features an in-house document ingestion pipeline, a hybrid dense-sparse search index (ChromaDB + BM25) with self-healing capabilities, a supervisor agent performing pairwise response generation with reinforcement alignment, an autonomous adversarial red-teaming auditor, and a gorgeous glassmorphic Single-Page Application (SPA) dashboard.

---

## 🚀 Key Features

*   **Layout-Aware PDF Ingestion:** Isolates table coordinates using bounding boxes via `pdfplumber` and formats table grids into structured Markdown. Splits text using capitalized headers to prevent layout bleed.
*   **Self-Healing Hybrid Search:** Fuses dense vector embeddings (ChromaDB) and sparse term frequencies (custom BM25 index) using **Reciprocal Rank Fusion (RRF)**. Dynamically drops and re-indexes the vector space upon credential/embedding model changes without user intervention.
*   **Pairwise RAG & Preference Alignment:** Synthesizes two responses side-by-side (Concise at $T=0.1$ vs. Conversational at $T=0.8$). Features a Human-in-the-Loop RLHF preference loop that dynamically injects user selections as few-shot rules.
*   **Autonomous Red-Teaming & Safety Auditing:** Runs exactly 6 adversarial attack vectors (hallucination baiting, prompt injections, and data leakage) and grades responses on a 0-10 safety scale for Faithfulness, Leakage Safety, and Injection Resistance.
*   **Premium Glassmorphic UI:** Features side-by-side bubbles, a radial gauge security dashboard, and a slide-out chronological Agent Reasoning Console streaming timeline logs in real-time.

---

## 🛠️ Tech Stack
*   **Backend:** Python 3.13, FastAPI, Uvicorn, Pydantic, requests
*   **Database:** ChromaDB (Vector Search) & Custom Local BM25 Keyword Search
*   **Ingestion:** pdfplumber, PyMuPDF (fitz)
*   **Embeddings:** SentenceTransformers (offline `all-MiniLM-L6-v2`), with dynamic overrides for OpenAI (`text-embedding-3-small`) and Gemini (`text-embedding-004`)
*   **Frontend:** HTML5, Vanilla CSS3 (glassmorphic theme), Vanilla JS (SPA)

---

## 📦 Directory Structure

```
DocShield/
├── backend/
│   ├── main.py (FastAPI Routes & Static Serving)
│   ├── pipeline/
│   │   └── parser.py (Layout-Aware Ingestion)
│   ├── database/
│   │   └── vector_store.py (ChromaDB + BM25 Hybrid Store)
│   ├── agents/
│   │   ├── agent_core.py (RAG Supervisor)
│   │   ├── red_teamer.py (Adversarial Query Generator)
│   │   └── evaluator.py (Safety Compliance Auditor)
│   └── tests/
│       └── verify.py (Automated Integration Tests)
├── frontend/
│   ├── index.html (SPA UI layout)
│   ├── style.css (Glassmorphic CSS rules)
│   └── app.js (SPA frontend logic)
├── requirements.txt (Dependencies list)
├── README.md (This file)
└── DocShieldIntro.md (Architectural design paper)
```

---

## 🚀 Setup & Execution

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/Vadera007/DocShield.git
cd DocShield
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Integration Tests
Verify all ingestion, retrieval, agent cores, red-teaming, and compliance safety grading work correctly:
```bash
python3 backend/tests/verify.py
```

### 3. Launch the Server
```bash
uvicorn backend.main:app --port 8090
```
Open **[http://localhost:8090/](http://localhost:8090/)** in your web browser to test the platform.

---

## 🛡️ RAG Security Scoring (RRF)
RAG search uses Reciprocal Rank Fusion (RRF) with a standard smoothing factor of $k=60$ to combine search results:
$$RRF(d) = \sum_{m \in M} \frac{1}{60 + r_m(d)}$$
where $M = \{\text{Vector Search}, \text{BM25}\}$ and $r_m(d)$ represents the rank index (1-based) of document $d$.
