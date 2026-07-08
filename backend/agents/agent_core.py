import os
import json
import re
from backend.database.vector_store import HybridStore

class DocAgentCore:
    def __init__(self, data_dir="data", openai_key=None, gemini_key=None):
        self.data_dir = data_dir
        self.openai_key = openai_key
        self.gemini_key = gemini_key
        self.store = HybridStore(data_dir=data_dir, openai_key=openai_key, gemini_key=gemini_key)
        self.preference_file = os.path.join(data_dir, "rlhf_preference_dataset.jsonl")

    def classify_query(self, query: str) -> str:
        query_lower = query.lower()
        tabular_keywords = ["table", "grid", "row", "column", "data", "list", "schedule", "schema", "numbers", "stats", "tabular"]
        for kw in tabular_keywords:
            if kw in query_lower:
                return "tabular"
        return "semantic"

    def load_preferences(self) -> list[dict]:
        prefs = []
        if os.path.exists(self.preference_file):
            try:
                with open(self.preference_file, "r") as f:
                    lines = f.readlines()
                # Get last 3 lines
                for line in lines[-3:]:
                    if line.strip():
                        prefs.append(json.loads(line))
            except Exception:
                pass
        return prefs

    def generate_system_instruction(self, is_precise: bool, preferences: list[dict]) -> str:
        if is_precise:
            style = "PRECISE & CONCISE style. Stick strictly to facts from the context. Use brief bullet points. Be direct, and avoid any conversational fluff."
        else:
            style = "CONVERSATIONAL & DETAILED style. Provide paragraph-based explanations, contextual background, and be conversational."
            
        instruction = f"You are DocShield's QA Assistant. Generate a response in a {style}\n"
        instruction += "CRITICAL RULE: If the answer cannot be verified from the context, state that you cannot answer based on the document.\n"
        
        if preferences:
            instruction += "\nFollow these guidelines based on past user preferences:\n"
            for p in preferences:
                instruction += f"- For prompt: \"{p['prompt']}\", prefer style like: \"{p['chosen']}\" rather than: \"{p['rejected']}\"\n"
                
        return instruction

    def execute_query_pairwise(self, query: str) -> dict:
        timeline = []
        
        # 1. Routing
        routing_decision = self.classify_query(query)
        timeline.append({
            "step": "Routing",
            "message": f"Classified query as '{routing_decision}'."
        })
        
        # 2. Retrieval
        timeline.append({
            "step": "Retrieval",
            "message": "Executing hybrid search (ChromaDB + BM25) with Reciprocal Rank Fusion..."
        })
        chunks = self.store.hybrid_search(query, top_k=4)
        citations = sorted(list(set([c["page"] for c in chunks])))
        
        timeline.append({
            "step": "Retrieval Matches",
            "message": f"Retrieved {len(chunks)} chunks from page(s): {', '.join(map(str, citations)) if citations else 'None'}."
        })
        
        # 3. Preferences
        timeline.append({
            "step": "Alignment Loaded",
            "message": "Checking for dynamic RLHF preference alignment guidelines..."
        })
        prefs = self.load_preferences()
        if prefs:
            timeline.append({
                "step": "Alignment Loaded",
                "message": f"Loaded {len(prefs)} preference guidelines from rlhf_preference_dataset.jsonl."
            })
        else:
            timeline.append({
                "step": "Alignment Loaded",
                "message": "No preference dataset found. Using default instructions."
            })
            
        # 4. Synthesis
        context_str = "\n\n".join([f"[Page {c['page']}] {c['content']}" for c in chunks])
        
        # Generate Response A & B
        resp_a = ""
        resp_b = ""
        
        has_keys = bool(self.openai_key or self.gemini_key)
        
        if has_keys:
            timeline.append({
                "step": "Synthesis",
                "message": f"Calling RAG cloud models (provider: {self.store.provider}) to generate responses..."
            })
            try:
                # Call Response A (Precise & Concise) - Temp 0.1
                system_a = self.generate_system_instruction(is_precise=True, preferences=prefs)
                messages_a = [
                    {"role": "system", "content": system_a},
                    {"role": "user", "content": f"Context:\n{context_str}\n\nQuery: {query}"}
                ]
                resp_a = self._call_llm(messages_a, temperature=0.1)
                
                # Call Response B (Conversational & Detailed) - Temp 0.8
                system_b = self.generate_system_instruction(is_precise=False, preferences=prefs)
                messages_b = [
                    {"role": "system", "content": system_b},
                    {"role": "user", "content": f"Context:\n{context_str}\n\nQuery: {query}"}
                ]
                resp_b = self._call_llm(messages_b, temperature=0.8)
                
            except Exception as e:
                timeline.append({
                    "step": "Auditor Checks",
                    "message": f"Synthesis API call failed: {str(e)}. Falling back to offline mock mode."
                })
                has_keys = False
                
        if not has_keys:
            timeline.append({
                "step": "Synthesis",
                "message": "No cloud API keys configured. Generating simulated layout-aware mock responses..."
            })
            resp_a, resp_b = self._generate_offline_mocks(query, chunks, routing_decision)
            
        timeline.append({
            "step": "Auditor Checks",
            "message": "RAG response pairs generated successfully. Ready for Security Auditing."
        })
        
        return {
            "response_a": resp_a,
            "response_b": resp_b,
            "citations": citations,
            "timeline": timeline,
            "retrieved_context": context_str
        }

    def _call_llm(self, messages, temperature=0.7):
        import requests
        if self.openai_key:
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            res = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": temperature
                },
                timeout=30
            )
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
            
        elif self.gemini_key:
            system_instruction = ""
            contents = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    system_instruction = content
                elif role == "user":
                    contents.append({"role": "user", "parts": [{"text": content}]})
                elif role == "assistant":
                    contents.append({"role": "model", "parts": [{"text": content}]})
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}"
            body = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature
                }
            }
            if system_instruction:
                body["systemInstruction"] = {"parts": [{"text": system_instruction}]}
                
            res = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=body,
                timeout=30
            )
            res.raise_for_status()
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            raise ValueError("No keys found")

    def _generate_offline_mocks(self, query: str, chunks: list[dict], routing_decision: str) -> tuple[str, str]:
        if not chunks:
            resp_a = "* No matches found in the document to answer your query."
            resp_b = "I apologize, but there are no matching segments in the uploaded document that address your query. Please make sure the document contains the relevant information."
            return resp_a, resp_b

        table_chunks = [c for c in chunks if c["type"] == "table"]
        
        if routing_decision == "tabular" and table_chunks:
            resp_a = "Here is the relevant table extracted from the document:\n\n" + table_chunks[0]["content"]
        else:
            bullets = []
            for c in chunks[:2]:
                text = c["content"]
                lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 10]
                for l in lines[:2]:
                    if l not in bullets:
                        # Strip headers or bullet symbols if any
                        clean_l = re.sub(r'^[\-\*\•\d\.\s]+', '', l)
                        bullets.append(f"- {clean_l}")
            if bullets:
                resp_a = "Key findings from the document:\n" + "\n".join(bullets)
            else:
                resp_a = f"- Found matching data on Page {chunks[0]['page']}: {chunks[0]['content'][:150]}..."
                
        summary_intro = f"Based on our search in the document, we identified key information on page {chunks[0]['page']} that relates to your query: \"{query}\"."
        body_points = []
        for c in chunks[:2]:
            body_points.append(f"Regarding the content on page {c['page']}, it indicates: {c['content'][:250].strip()}...")
            
        resp_b = f"{summary_intro}\n\n" + "\n\n".join(body_points)
        resp_b += "\n\nLet me know if you would like me to go deeper into these sections or run an adversarial security audit."
        
        return resp_a, resp_b
