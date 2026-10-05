import json
import time
import requests
from pharma_validator import FormulationValidator

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"

scenario = """Target: Paracetamol / Acetaminophen (500 mg immediate-release oral tablet).
Barriers:
- High unit dose (500 mg): severe pill mass constraint. Must achieve >=75% drug loading to keep total tablet mass <= 650 mg.
- Poor compressibility and capping: pure Paracetamol monoclinic Form I has low plasticity and high elastic recovery during high-speed tableting.
- Bitter taste.
Objective:
Design a compact direct-compression or wet-granulated tablet matrix (dose: 500 mg) that avoids excessive excipient mass (max 650 mg total) using FDA IID compliant binders and disintegrants."""

FORMULATOR_SYSTEM = """You are a Senior Pharmaceutical Formulation Chemist.
Deliver ONLY a valid JSON object. No markdown, no filler prose.
JSON Schema:
{
  "drug": "Paracetamol",
  "drug_dose_mg": 500.0,
  "carrier": string (e.g. "Povidone (PVP K30)" or "Pregelatinized Starch"),
  "polymer_ratio": string (e.g. "1:0.1" or "0.05"),
  "surfactant": string (or superdisintegrant, e.g. "Croscarmellose Sodium"),
  "surfactant_mg": float,
  "total_mass_mg": float,
  "physical_state": "Immediate-Release Tablet",
  "patent_workaround": string (rationale on high drug loading and compressibility)
}"""

CRITIC_SYSTEM = """You are a Ruthless FDA Auditor. Output ONLY concise bullet points and a final verdict.
Audit Criteria:
1. Verify tablet mass burden vs swallowability (500 mg API must not exceed 650 mg total).
2. Verify excipients against FDA IID limits.
3. Check tableting physics: capping, lamination, and binder efficacy."""

print("[*] Generating Formulator Pitch for Paracetamol 500 mg...")
t0 = time.time()
res = requests.post(OLLAMA_API, json={
    "model": MODEL_NAME,
    "prompt": f"Scenario:\n{scenario}",
    "system": FORMULATOR_SYSTEM,
    "stream": False,
    "options": {"temperature": 0.2, "num_predict": 400}
}, timeout=60).json()

raw_text = res.get("response", "").strip()
print(f"Generated in {time.time()-t0:.1f}s")
print(raw_text)

# Extract and validate
import re
match = re.search(r"\{.*\}", raw_text, re.DOTALL)
if match:
    f_json = json.loads(match.group(0))
    audit = FormulationValidator.audit_formulation(f_json)
    print("\n--- PYTHON AUDIT REPORT ---")
    print("Is Valid:", audit["is_valid"])
    print("Fatal Errors:", audit["fatal_errors"])
    print("Findings:", audit["findings"])
    print(f"Calculated Core: {audit['calculated_core_mass_mg']} mg | Effective Unit: {audit['effective_unit_mass_mg']} mg")
