"""Direct DeepSeek API test."""
import httpx, json

client = httpx.Client(
    base_url="https://api.deepseek.com",
    headers={
        "Authorization": "Bearer sk-5d920ab435b24002b9e99089365e44c6",
        "Content-Type": "application/json",
    },
    timeout=120,
)

payload = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": 'Say hello as JSON: {"greeting": "hello"}'}],
    "temperature": 0.0,
    "max_tokens": 100,
    "stream": False,
}

print("Sending...")
r = client.post("/v1/chat/completions", json=payload)
print(f"Status: {r.status_code}")
print(f"Content length: {len(r.text)}")
print(f"Response: {r.text[:500]}")
client.close()
