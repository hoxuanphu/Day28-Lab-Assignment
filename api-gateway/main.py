from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from prometheus_fastapi_instrumentator import Instrumentator
import httpx, os, time, langsmith

app = FastAPI(title="AI Platform API Gateway")
Instrumentator().instrument(app).expose(app)  # Integration 9: Prometheus

VLLM_URL = os.environ["VLLM_URL"]
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")

class ChatRequest(BaseModel):
    query: str
    embedding: List[float] = [0.0] * 384

@app.post("/api/v1/chat")
async def chat(body: ChatRequest):
    query = body.query
    embedding = body.embedding
    start = time.time()

    # 1. Vector search
    async with httpx.AsyncClient() as client:
        try:
            search_resp = await client.post(f"{QDRANT_URL}/collections/documents/points/search", json={
                "vector": embedding,
                "limit": 3
            })
            context = search_resp.json().get("result", [])
        except Exception as e:
            print("Vector search error:", e)
            context = []

    # 2. LLM inference
    prompt = f"Context: {context}\n\nQuery: {query}"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            llm_resp = await client.post(f"{VLLM_URL}/v1/chat/completions", json={
                "model": "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                "messages": [{"role": "user", "content": prompt}]
            })
            result = llm_resp.json()
            answer = result["choices"][0]["message"]["content"]
            model_name = result["model"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM serving error: {str(e)}")

    latency = (time.time() - start) * 1000

    return {
        "answer": answer,
        "latency_ms": round(latency, 2),
        "model": model_name
    }

@app.get("/health")
def health():
    return {"status": "ok"}
