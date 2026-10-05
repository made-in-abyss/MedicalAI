import time
import requests

t0 = time.time()
res = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2.5:3b",
        "prompt": "You are a pharma chemist. Output a compact JSON object for an amorphous solid dispersion of Ibrutinib 140mg bypassing Form A polymorph claims. Keys: drug, dose_mg, polymer, ratio, mass_mg, patent_workaround. Output raw JSON only.",
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 250}
    },
    timeout=60
).json()
elapsed = time.time() - t0
print(f"Time: {elapsed:.2f}s")
print(res.get("response", ""))
