import os
import re
import json
import math
import shutil
import requests

class SimpleBM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_len = [len(doc) for doc in corpus]
        self.avg_doc_len = sum(self.doc_len) / len(corpus) if corpus else 0
        self.doc_freqs = []
        self.idf = {}
        self.nd = len(corpus)
        self.initialize()

    def initialize(self):
        df = {}
        for doc in self.corpus:
            frequencies = {}
            for word in doc:
                frequencies[word] = frequencies.get(word, 0) + 1
            self.doc_freqs.append(frequencies)
            for word in frequencies:
                df[word] = df.get(word, 0) + 1
        for word, freq in df.items():
            self.idf[word] = math.log(1 + (self.nd - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query_tokens):
        scores = []
        for i in range(self.nd):
            score = 0.0
            doc_freq = self.doc_freqs[i]
            d_len = self.doc_len[i]
            for word in query_tokens:
                if word in doc_freq:
                    tf = doc_freq[word]
                    numerator = self.idf.get(word, 0) * tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * d_len / self.avg_doc_len)
                    score += numerator / denominator
            scores.append(score)
        return scores

class EmbeddingEngine:
    def __init__(self, openai_key=None, gemini_key=None):
        self.openai_key = openai_key
        self.gemini_key = gemini_key
        self._local_model = None

    def get_dimension(self):
        if self.openai_key:
            return 1536
        elif self.gemini_key:
            return 768
        else:
            return 384

    def get_provider_name(self):
        if self.openai_key:
            return "openai"
        elif self.gemini_key:
            return "gemini"
        else:
            return "local"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        
        provider = self.get_provider_name()
        if provider == "openai":
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            res = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json={"model": "text-embedding-3-small", "input": texts},
                timeout=15
            )
            res.raise_for_status()
            data = res.json()
            return [item["embedding"] for item in data["data"]]
            
        elif provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key={self.gemini_key}"
            reqs = []
            for t in texts:
                reqs.append({
                    "model": "models/text-embedding-004",
                    "content": {"parts": [{"text": t}]}
                })
            res = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={"requests": reqs},
                timeout=15
            )
            res.raise_for_status()
            data = res.json()
            return [e["values"] for e in data["embeddings"]]
            
        else:
            if self._local_model is None:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings = self._local_model.encode(texts)
            return embeddings.tolist()

class HybridStore:
    def __init__(self, data_dir="data", openai_key=None, gemini_key=None):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.metadata_path = os.path.join(data_dir, "db_metadata.json")
        self.chunks_path = os.path.join(data_dir, "parsed_chunks.json")
        
        self.openai_key = openai_key
        self.gemini_key = gemini_key
        self.embed_engine = EmbeddingEngine(openai_key, gemini_key)
        
        self.provider = self.embed_engine.get_provider_name()
        self.dimension = self.embed_engine.get_dimension()
        
        self.chroma_path = os.path.join(data_dir, "chroma")
        
        # Check if we need to heal
        self.check_and_heal()
        
        # Init ChromaDB
        import chromadb
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="docshield_collection",
            metadata={"hnsw:space": "cosine"}
        )
        
        # BM25
        self.chunks = []
        self.bm25 = None
        self.load_chunks_and_build_bm25()

    def check_and_heal(self):
        heal_needed = False
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r") as f:
                    meta = json.load(f)
                if meta.get("provider") != self.provider or meta.get("dimension") != self.dimension:
                    heal_needed = True
            except Exception:
                heal_needed = True
        elif os.path.exists(self.chroma_path) and len(os.listdir(self.chroma_path)) > 0:
            heal_needed = True
            
        if heal_needed:
            print(f"[Self-Healing] Embedding configuration changed. Recreating ChromaDB at {self.chroma_path}...")
            if os.path.exists(self.chroma_path):
                shutil.rmtree(self.chroma_path)
            self.save_metadata()
            
            if os.path.exists(self.chunks_path):
                try:
                    with open(self.chunks_path, "r") as f:
                        chunks = json.load(f)
                    print(f"[Self-Healing] Found {len(chunks)} cached chunks. Auto re-indexing...")
                    self.chunks_to_reindex = chunks
                except Exception:
                    self.chunks_to_reindex = []
            else:
                self.chunks_to_reindex = []
        else:
            self.save_metadata()
            self.chunks_to_reindex = []

    def save_metadata(self):
        with open(self.metadata_path, "w") as f:
            json.dump({"provider": self.provider, "dimension": self.dimension}, f)

    def load_chunks_and_build_bm25(self):
        if os.path.exists(self.chunks_path):
            try:
                with open(self.chunks_path, "r") as f:
                    self.chunks = json.load(f)
            except Exception:
                self.chunks = []
        
        if self.chunks:
            corpus = [self.tokenize(c["content"]) for c in self.chunks]
            self.bm25 = SimpleBM25(corpus)
            
        if self.chunks_to_reindex:
            self.index_chunks(self.chunks_to_reindex, save_chunks=False)
            self.chunks_to_reindex = []

    def tokenize(self, text: str) -> list[str]:
        text = text.lower()
        return re.findall(r'\b\w+\b', text)

    def index_chunks(self, chunks: list[dict], save_chunks=True):
        if not chunks:
            return
            
        # Drop previous vectors to index fresh chunks
        try:
            self.chroma_client.delete_collection("docshield_collection")
        except Exception:
            pass
            
        self.collection = self.chroma_client.get_or_create_collection(
            name="docshield_collection",
            metadata={"hnsw:space": "cosine"}
        )
            
        texts = [c["content"] for c in chunks]
        embeddings = self.embed_engine.embed_documents(texts)
        
        ids = [c["id"] for c in chunks]
        metadatas = [{"page": c["page"], "type": c["type"]} for c in chunks]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        
        if save_chunks:
            self.chunks = chunks
            with open(self.chunks_path, "w") as f:
                json.dump(chunks, f)
            
            corpus = [self.tokenize(c["content"]) for c in self.chunks]
            self.bm25 = SimpleBM25(corpus)

    def hybrid_search(self, query: str, top_k=5) -> list[dict]:
        if not self.chunks:
            return []
            
        # 1. Vector Search
        query_vector = self.embed_engine.embed_documents([query])[0]
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k * 2, len(self.chunks))
        )
        
        # 2. BM25 Search
        bm25_results = []
        if self.bm25:
            query_tokens = self.tokenize(query)
            scores = self.bm25.get_scores(query_tokens)
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            bm25_results = [self.chunks[idx]["id"] for idx in ranked_indices[:top_k * 2]]
                
        # 3. Reciprocal Rank Fusion (RRF)
        from collections import defaultdict
        rrf_scores = defaultdict(float)
        
        # Ensure a standard smoothing factor of k=60
        vector_results = results["ids"][0] if (results and results["ids"] and results["ids"][0]) else []
        for rank, doc_id in enumerate(vector_results):
            rrf_scores[doc_id] += 1.0 / (60 + rank + 1)
            
        for rank, doc_id in enumerate(bm25_results):
            rrf_scores[doc_id] += 1.0 / (60 + rank + 1)
            
        sorted_cids = sorted(rrf_scores.keys(), key=lambda doc_id: rrf_scores[doc_id], reverse=True)
        
        chunk_map = {c["id"]: c for c in self.chunks}
        final_results = []
        for cid in sorted_cids[:top_k]:
            if cid in chunk_map:
                final_results.append({
                    "id": cid,
                    "page": chunk_map[cid]["page"],
                    "type": chunk_map[cid]["type"],
                    "content": chunk_map[cid]["content"],
                    "rrf_score": rrf_scores[cid]
                })
        return final_results
