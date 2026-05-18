# %% [markdown]
# # Lab #28 — Full Platform Integration Sprint: GPU Server Setup
# Chạy file này trên Google Colab có bật GPU T4 để khởi chạy vLLM & Embedding Service qua 1 Tunnel duy nhất.

# %%
# 1. Cài đặt các thư viện cần thiết cho môi trường Cloud
print("--- 1. Cài đặt các thư viện cần thiết ---")
!pip install -q vllm fastapi uvicorn pyngrok sentence-transformers requests

# %%
# 2. Cấu hình ngrok Token cá nhân
# Hãy thay thế chuỗi dưới đây bằng Token lấy từ dashboard.ngrok.com
from pyngrok import ngrok
NGROK_TOKEN = "YOUR_NGROK_TOKEN"
ngrok.set_auth_token(NGROK_TOKEN)
print("Cấu hình ngrok Token thành công!")

# %%
# 3. Khởi động vLLM Server chạy ngầm (port 8001)
import subprocess
import threading
import time

print("--- 2. Khởi động vLLM Server (Qwen2.5-7B-Instruct-GPTQ-Int4) ---")

def run_vllm():
    subprocess.run([
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
        "--port", "8001",
        "--max-model-len", "2048",
        "--gpu-memory-utilization", "0.80"
    ])

# Chạy vLLM trong luồng phụ (thread)
vllm_thread = threading.Thread(target=run_vllm, daemon=True)
vllm_thread.start()

print("Đang tải model Qwen2.5-7B-Instruct... (Quá trình này mất khoảng 2 phút, vui lòng đợi)")
time.sleep(100)  # Chờ 100 giây để model được nạp hoàn toàn vào VRAM GPU
print("vLLM Server đã khởi chạy xong tại port 8001!")

# %%
# 4. Khởi động FastAPI Unified Proxy Service & Expose Port 8000 qua ngrok
from fastapi import FastAPI, Request
from fastapi.responses import Response
from sentence_transformers import SentenceTransformer
import uvicorn
import requests

print("--- 3. Khởi động FastAPI Unified Proxy Service (bge-small-en-v1.5 + vLLM Proxy) ---")

app = FastAPI(title="Unified Colab AI Service")
model = SentenceTransformer("BAAI/bge-small-en-v1.5")

@app.post("/embed")
def embed(data: dict):
    texts = data["texts"]
    embeddings = model.encode(texts).tolist()
    return {"embeddings": embeddings}

# Proxy cho vLLM Chat Completions
@app.post("/v1/chat/completions")
async def proxy_chat(request: Request):
    body = await request.json()
    resp = requests.post("http://localhost:8001/v1/chat/completions", json=body, timeout=60)
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")

# Proxy cho vLLM Models
@app.get("/v1/models")
async def proxy_models():
    resp = requests.get("http://localhost:8001/v1/models", timeout=10)
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")

def run_unified_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Chạy Unified API trong luồng phụ
threading.Thread(target=run_unified_server, daemon=True).start()
time.sleep(5)

# Expose port 8000 qua ngrok (Chỉ cần 1 tunnel duy nhất!)
unified_tunnel = ngrok.connect(8000, "http")
print("\n" + "="*80)
# In ra hướng dẫn dán link
print(f">>> ĐÂY LÀ ĐƯỜNG LINK DUY NHẤT BẠN CẦN!")
print(f"Hãy sao chép link dưới đây và dán vào CẢ 2 dòng trong file .env trên Local:")
print(f"VLLM_NGROK_URL={unified_tunnel.public_url}")
print(f"EMBED_NGROK_URL={unified_tunnel.public_url}")
print("="*80 + "\n")
print("--- TẤT CẢ DỊCH VỤ ĐÃ SẴN SÀNG! GIỮ CHO TAB COLAB LUÔN CHẠY KHI LÀM BÀI ---")
