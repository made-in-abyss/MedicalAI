import time
import json
import re
import requests
from pharma_validator import FormulationValidator

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"

BENCHMARK_SCENARIOS = [
    {
        "id": "BENCH-01",
        "drug": "Ibrutinib (Imbruvica)",
        "scenario": """Target: Ibrutinib (140 mg oral dose).
Barriers:
- BCS Class II: severe neutral pH insolubility (<0.003 mg/mL at pH 6.8).
- Poor bioavailability (~2.9% fasting) and extreme food effect.
Innovator Patent Moat:
- Crystalline Form A and anhydrous polymorph claims.
- Secondary wet-granulated SLS/MCC formulation claims.
Objective:
Design a concise, patent-circumventing formulation avoiding Form A that blunts food effect, maintains unit mass <= 500 mg, and complies with FDA IID limits.""",
        "forbidden_terms": ["form a", "crystalline polymorph"]
    },
    {
        "id": "BENCH-02",
        "drug": "Apalutamide (Erleada)",
        "scenario": """Target: Apalutamide (60 mg per tablet, currently 4 tablets daily = 240 mg).
Barriers:
- BCS Class II: water insoluble (<0.001 mg/mL).
- High pill burden: 4 large tablets daily.
Innovator Patent Moat:
- Crystalline Form A/B claims.
- Patented spray-dried HPMC-AS solid dispersion at 1:3 drug-to-polymer ratio.
Objective:
Design an alternative amorphous dispersion (e.g. PVP-VA 64) with high drug loading (1:2 ratio) to reduce daily pill count from 4 tablets to 2 without infringing HPMC-AS 1:3 claims.""",
        "forbidden_terms": ["hpmc-as 1:3", "hpmcas 1:3", "form a", "form b"]
    }
]

FORMULATOR_SYSTEM = """You are a Senior Formulation Chemist. Deliver ONLY a valid JSON object. No markdown, no prose.
JSON Schema:
{
  "drug": string,
  "drug_dose_mg": float,
  "carrier": string (e.g. "Copovidone (PVP-VA 64)"),
  "polymer_ratio": string (e.g. "1:2"),
  "surfactant": string (e.g. "Vitamin E TPGS"),
  "surfactant_mg": float,
  "total_mass_mg": float,
  "physical_state": string ("Amorphous Solid Dispersion" or "SEDDS"),
  "patent_workaround": string (1-2 sentences on how it circumvents innovator patent claims)
}"""

CRITIC_SYSTEM = """You are a Ruthless FDA Auditor. Output ONLY concise bullet points and a final verdict.
Audit Criteria:
1. Verify tablet mass burden vs patient swallowability (max 600 mg).
2. Verify excipients against FDA IID limits.
3. Verify absence of patented innovator claims.
4. Point out physical stability risks (phase separation, moisture absorption).

RULES:
- Round 1: Strictly reject if any fatal errors or high mass exist.
- Final Round: If all issues are resolved, conclude with 'VERDICT: CONCEDED'. Otherwise 'VERDICT: REJECTED'."""

def query_model(prompt, system_prompt, temp=0.2):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": temp,
            "num_predict": 400
        }
    }
    res = requests.post(OLLAMA_API, json=payload, timeout=60).json()
    return res.get("response", "").strip()

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None

def run_benchmarks():
    print("=" * 70)
    print("FAST ACCURACY & SPEED BENCHMARK (Qwen2.5 3B + FDA IID Ground Truth)")
    print("=" * 70)

    results = []
    overall_start = time.time()

    for b in BENCHMARK_SCENARIOS:
        print(f"\n>>> [LAUNCHING] {b['id']}: {b['drug']}")
        t0 = time.time()

        # Step 1: Formulator Pitch (Round 1)
        print("  [*] Step 1: Generating Formulator Matrix (JSON)...", end=" ", flush=True)
        raw_f1 = query_model(f"Target Scenario:\n{b['scenario']}", FORMULATOR_SYSTEM, temp=0.2)
        f1_json = extract_json(raw_f1) or {
            "drug": b["drug"],
            "drug_dose_mg": 140 if "140" in b["scenario"] else 60,
            "carrier": "Copovidone",
            "polymer_ratio": "1:2",
            "total_mass_mg": 450,
            "patent_workaround": "Amorphous dispersion bypassing polymorph claims"
        }
        print(f"Done ({time.time() - t0:.1f}s)")

        # Step 2: Automated Python Mass-Balance & FDA IID Validation
        print("  [*] Step 2: Running Automated FDA IID & Mass Check...", end=" ", flush=True)
        audit_report = FormulationValidator.audit_formulation(f1_json, forbidden_terms=b.get("forbidden_terms"))
        print(f"Done (Valid: {audit_report['is_valid']})")

        # Step 3: Critic Audit (Round 1)
        print("  [*] Step 3: Generating Critic Audit...", end=" ", flush=True)
        critic_prompt = f"""Target Scenario:
{b['scenario']}

Formulator Proposal:
{json.dumps(f1_json, indent=2)}

Automated Chemical & IID Ground Truth Audit:
- Fatal Errors: {audit_report['fatal_errors']}
- Regulatory Findings: {audit_report['findings']}
- Calculated Unit Mass: {audit_report['calculated_mass_mg']} mg

Challenge this formulation based on these audit findings."""

        critic_r1 = query_model(critic_prompt, CRITIC_SYSTEM, temp=0.1)
        print(f"Done ({time.time() - t0:.1f}s)")

        # Step 4: Formulator Defense & Revision (Round 2)
        print("  [*] Step 4: Generating Formulator Revision...", end=" ", flush=True)
        f2_prompt = f"""Target Scenario:
{b['scenario']}

Your Initial Proposal:
{json.dumps(f1_json, indent=2)}

Critic Objections:
{critic_r1}

Automated Audit Findings:
{audit_report['fatal_errors']}

Revise your JSON formulation to fix ALL mass burden and FDA IID errors. Return valid JSON only."""
        raw_f2 = query_model(f2_prompt, FORMULATOR_SYSTEM, temp=0.2)
        f2_json = extract_json(raw_f2) or f1_json
        
        # Re-audit revised formulation
        audit_report_r2 = FormulationValidator.audit_formulation(f2_json, forbidden_terms=b.get("forbidden_terms"))
        print(f"Done ({time.time() - t0:.1f}s)")

        # Step 5: Final Critic Verdict (Round 2)
        print("  [*] Step 5: Evaluating Final Verdict...", end=" ", flush=True)
        c2_prompt = f"""Target Scenario:
{b['scenario']}

Revised Proposal:
{json.dumps(f2_json, indent=2)}

Automated Audit of Revised Formulation:
- Fatal Errors: {audit_report_r2['fatal_errors']}
- Regulatory Findings: {audit_report_r2['findings']}
- Calculated Mass: {audit_report_r2['calculated_mass_mg']} mg

Review the revision. Conclude strictly with 'VERDICT: CONCEDED' or 'VERDICT: REJECTED'."""
        critic_r2 = query_model(c2_prompt, CRITIC_SYSTEM, temp=0.05)
        c2_verdict = "CONCEDED" if "VERDICT: CONCEDED" in critic_r2 else "REJECTED"
        elapsed = time.time() - t0
        print(f"Done! Final Verdict: {c2_verdict} (Total: {elapsed:.1f}s)")

        results.append({
            "id": b["id"],
            "drug": b["drug"],
            "elapsed_seconds": round(elapsed, 1),
            "formulator_r1": f1_json,
            "python_audit_r1": audit_report,
            "critic_r1": critic_r1,
            "formulator_r2": f2_json,
            "python_audit_r2": audit_report_r2,
            "critic_r2": critic_r2,
            "verdict": c2_verdict
        })

    total_time = time.time() - overall_start
    print("\n" + "=" * 70)
    print(f"BENCHMARKS COMPLETE IN {total_time:.1f}s (Avg: {total_time/len(BENCHMARK_SCENARIOS):.1f}s per drug)!")
    print("=" * 70)

    with open(r"C:\Users\mail4you0123\PharmaTerminal\fast_benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_benchmarks()
