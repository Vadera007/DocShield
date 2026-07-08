import os
import shutil
import json
from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.pipeline.parser import parse_pdf
from backend.agents.agent_core import DocAgentCore
from backend.agents.red_teamer import RedTeamer
from backend.agents.evaluator import AuditorAgent

app = FastAPI(title="DocShield API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

class QueryRequest(BaseModel):
    query: str

class FeedbackRequest(BaseModel):
    prompt: str
    chosen: str
    rejected: str

@app.post("/api/upload")
async def upload(
    file: UploadFile = File(...),
    x_openai_key: str = Header(None, alias="X-OpenAI-Key"),
    x_gemini_key: str = Header(None, alias="X-Gemini-Key")
):
    try:
        temp_path = os.path.join(DATA_DIR, file.filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Parse PDF
        chunks = parse_pdf(temp_path)
        if not chunks:
            raise HTTPException(status_code=400, detail="No text or tables could be extracted from this PDF.")
            
        # Index chunks
        agent_core = DocAgentCore(data_dir=DATA_DIR, openai_key=x_openai_key, gemini_key=x_gemini_key)
        agent_core.store.index_chunks(chunks)
        
        # Save filename in metadata
        meta_path = os.path.join(DATA_DIR, "doc_info.json")
        with open(meta_path, "w") as f:
            json.dump({"filename": file.filename, "chunk_count": len(chunks)}, f)
            
        return {"status": "success", "filename": file.filename, "chunk_count": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
def query_doc(
    req: QueryRequest,
    x_openai_key: str = Header(None, alias="X-OpenAI-Key"),
    x_gemini_key: str = Header(None, alias="X-Gemini-Key")
):
    try:
        agent_core = DocAgentCore(data_dir=DATA_DIR, openai_key=x_openai_key, gemini_key=x_gemini_key)
        res = agent_core.execute_query_pairwise(req.query)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback")
def save_feedback(req: FeedbackRequest):
    try:
        preference_file = os.path.join(DATA_DIR, "rlhf_preference_dataset.jsonl")
        with open(preference_file, "a") as f:
            f.write(json.dumps({
                "prompt": req.prompt,
                "chosen": req.chosen,
                "rejected": req.rejected
            }) + "\n")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/redteam")
def execute_redteam_audit(
    x_openai_key: str = Header(None, alias="X-OpenAI-Key"),
    x_gemini_key: str = Header(None, alias="X-Gemini-Key")
):
    try:
        # Check if chunks are loaded
        chunks_path = os.path.join(DATA_DIR, "parsed_chunks.json")
        if not os.path.exists(chunks_path):
            raise HTTPException(status_code=400, detail="No document has been uploaded yet.")
            
        with open(chunks_path, "r") as f:
            chunks = json.load(f)
            
        # Take first 5 chunks for context
        context_str = "\n\n".join([c["content"] for c in chunks[:5]])
        
        red_teamer = RedTeamer(openai_key=x_openai_key, gemini_key=x_gemini_key)
        queries_dict = red_teamer.generate_adversarial_queries(context_str)
        
        auditor = AuditorAgent(openai_key=x_openai_key, gemini_key=x_gemini_key)
        agent_core = DocAgentCore(data_dir=DATA_DIR, openai_key=x_openai_key, gemini_key=x_gemini_key)
        
        audit_logs = []
        faithfulness_scores = []
        leakage_scores = []
        injection_scores = []
        
        for category, queries in queries_dict.items():
            for q in queries:
                rag_res = agent_core.execute_query_pairwise(q)
                ans_a = rag_res["response_a"]
                ans_b = rag_res["response_b"]
                context_used = rag_res["retrieved_context"]
                
                audit_a = auditor.audit_response(q, ans_a, context_used)
                audit_b = auditor.audit_response(q, ans_b, context_used)
                
                audit_logs.append({
                    "query": q,
                    "category": category,
                    "response_a": ans_a,
                    "response_b": ans_b,
                    "audit_a": audit_a,
                    "audit_b": audit_b
                })
                
                faithfulness_scores.append((audit_a["faithfulness"]["score"] + audit_b["faithfulness"]["score"]) / 2)
                leakage_scores.append((audit_a["data_leakage"]["score"] + audit_b["data_leakage"]["score"]) / 2)
                injection_scores.append((audit_a["injection_resistance"]["score"] + audit_b["injection_resistance"]["score"]) / 2)
                
        avg_faith = sum(faithfulness_scores) / len(faithfulness_scores) if faithfulness_scores else 0
        avg_leak = sum(leakage_scores) / len(leakage_scores) if leakage_scores else 0
        avg_inject = sum(injection_scores) / len(injection_scores) if injection_scores else 0
        
        overall_safety = (avg_faith + avg_leak + avg_inject) / 3 * 10
        
        return {
            "security_score": round(overall_safety, 1),
            "sub_stats": {
                "faithfulness": round(avg_faith, 2),
                "leakage_resistance": round(avg_leak, 2),
                "injection_resistance": round(avg_inject, 2)
            },
            "audit_logs": audit_logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clear")
def clear_state():
    try:
        meta_path = os.path.join(DATA_DIR, "doc_info.json")
        if os.path.exists(meta_path):
            os.remove(meta_path)
        chunks_path = os.path.join(DATA_DIR, "parsed_chunks.json")
        if os.path.exists(chunks_path):
            os.remove(chunks_path)
            
        try:
            import chromadb
            chroma_path = os.path.join(DATA_DIR, "chroma")
            chroma_client = chromadb.PersistentClient(path=chroma_path)
            chroma_client.delete_collection("docshield_collection")
        except Exception:
            pass
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")

def get_status():
    meta_path = os.path.join(DATA_DIR, "doc_info.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            info = json.load(f)
        return {"status": "active", "document": info["filename"], "chunks": info["chunk_count"]}
    return {"status": "inactive", "document": None, "chunks": 0}

# Create static directory if not exists
os.makedirs("frontend", exist_ok=True)
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
