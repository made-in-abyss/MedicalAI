import time
import json
import re
import requests

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "deepseek-r1:7b"

BENCHMARK_SCENARIOS = [
    {
        "id": "BENCH-01",
        "drug": "Ibrutinib (Imbruvica)",
        "scenario": """Target: Ibrutinib (140 mg oral dose).
Barriers:
- BCS Class II: extreme pH-dependent insolubility (<0.003 mg/mL at neutral pH 6.8).
- High CYP3A4 first-pass clearance (bioavailability only ~2.9% fasting).
- Extreme food effect (AUC doubles with high-fat meals).
Innovator Patent Moat:
- Crystalline Form A and anhydrous polymorph claims.
- Secondary wet-granulated SLS/MCC formulation claims.
Objective:
Design a concise, patent-circumventing formulation avoiding Form A that blunts food effect and complies with FDA IID limits."""
    },
    {
        "id": "BENCH-02",
        "drug": "Apalutamide (Erleada)",
        "scenario": """Target: Apalutamide (60 mg oral dose).
Barriers:
- BCS Class II: essentially insoluble in water (<0.001 mg/mL across physiological pH).
- Severe pill burden: currently requires 4 large tablets daily (240 mg total).
Innovator Patent Moat:
- Crystalline polymorph Form A/B claims.
- Spray-dried HPMC-AS solid dispersion matrix claims (patented 1:3 drug-to-polymer ratio).
Objective:
Design an alternative amorphous dispersion (e.g. copovidone PVP-VA or lipid SEDDS) achieving high drug loading to reduce daily pill count from 4 tablets to 2 without infringing the patented HPMC-AS 1:3 matrix."""
    },
    {
        "id": "BENCH-03",
        "drug": "Paclitaxel (Taxol/Abraxane)",
        "scenario": """Target: Paclitaxel (Oncology IV infusion).
Barriers:
- Extreme lipophilicity (water insoluble <0.0003 mg/mL).
- High vehicle toxicity: Innovator formulation requires Cremophor EL (polyoxyethylated castor oil) + ethanol, causing severe acute hypersensitivity and peripheral neuropathy requiring steroid premedication.
Innovator Patent Moat:
- Celgene/BMS holds claims on human serum albumin nanoparticle-bound paclitaxel (Abraxane).
Objective:
Design a solvent-free, albumin-free polymeric micelle or liposomal alternative that avoids Cremophor EL toxicity, circumvents albumin nanoparticle patents, and utilizes FDA IID approved lipids/polymers."""
    }
]

FORMULATOR_SYSTEM = """You are a Senior Pharmaceutical Formulation Chemist.
Deliver ONLY concise, core formulation data. No conversational filler.
MANDATORY SPECIFICATIONS:
1. Active Drug & Dose (mg).
2. Carrier Matrix & Ratio (w/w).
3. Surfactant / Precipitation Inhibitor (FDA IID compliant).
4. Physical State (amorphous solid dispersion, SEDDS, or micellar).
5. 2-sentence rationale on how it circumvents innovator patent claims.
Always think step-by-step inside <think>...</think> tags first."""

CRITIC_SYSTEM = """You are a Ruthless FDA Safety Auditor & Senior Toxicologist. Assume this formulation WILL FAIL.
BE CONCISE: Output ONLY bulleted objections and essential chemical trivia/facts. No polite intros.
MANDATORY AUDIT CRITERIA:
1. Verify drug class & biological target.
2. Tablet/Vial Mass Burden: calculate drug+excipient load.
3. Thermodynamic Stability: phase separation, moisture plasticization, precipitation risk.
4. Inactive Ingredient Limits: check excipient doses vs FDA Inactive Ingredient Database (IID).

MANDATORY RULE: You are STRICTLY FORBIDDEN from conceding in Round 1. Find at least 2 fatal flaws.
TERMINATION:
Conclude ONLY with:
'VERDICT: CONCEDED' (Only if ALL objections are empirically resolved in later rounds)
or
'VERDICT: REJECTED'
Always think step-by-step inside <think>...</think> tags first."""

def strip_thinking(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

def query_agent(prompt, system_prompt, temp):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": True,
        "options": {
            "temperature": temp,
            "top_p": 0.9,
            "num_ctx": 4096
        }
    }
    res = requests.post(OLLAMA_API, json=payload, stream=True, timeout=600)
    full_text = ""
    for line in res.iter_lines():
        if line:
            chunk = json.loads(line.decode("utf-8"))
            full_text += chunk.get("response", "")
    return full_text

def run_3_benchmarks():
    print("=" * 70)
    print("RUNNING 3 ADVERSARIAL PHARMACEUTICAL BENCHMARKS (DeepSeek-R1 7B)")
    print("=" * 70)

    results = []
    for b in BENCHMARK_SCENARIOS:
        print(f"\n>>> [LAUNCHING] {b['id']}: {b['drug']}")
        start_time = time.time()
        
        # Round 1: Formulator
        print("  [1/3] Generating Formulator Pitch...")
        raw_f1 = query_agent(f"Target:\n{b['scenario']}", FORMULATOR_SYSTEM, temp=0.15)
        clean_f1 = strip_thinking(raw_f1)
        
        # Round 1: Critic
        print("  [2/3] Generating Critic Audit...")
        raw_c1 = query_agent(f"Target Drug:\n{b['scenario']}\n\nProposed Matrix:\n{clean_f1}", CRITIC_SYSTEM, temp=0.05)
        clean_c1 = strip_thinking(raw_c1)
        c1_verdict = "CONCEDED" if "VERDICT: CONCEDED" in clean_c1 else "REJECTED"

        # Round 2: Formulator Defense
        print(f"  [3/3] Generating Formulator Counter-Defense (Critic was {c1_verdict})...")
        raw_f2 = query_agent(
            f"Target:\n{b['scenario']}\n\nCurrent Matrix:\n{clean_f1}\n\nCritic Objections:\n{clean_c1}\n\nResolve every objection concisely.",
            FORMULATOR_SYSTEM,
            temp=0.15
        )
        clean_f2 = strip_thinking(raw_f2)

        # Round 2: Final Critic Audit
        raw_c2 = query_agent(f"Target:\n{b['scenario']}\n\nRevised Matrix:\n{clean_f2}", CRITIC_SYSTEM, temp=0.05)
        clean_c2 = strip_thinking(raw_c2)
        c2_verdict = "CONCEDED" if "VERDICT: CONCEDED" in clean_c2 else "REJECTED"

        elapsed = time.time() - start_time
        print(f"  [DONE] {b['id']} finished in {elapsed:.1f}s. Final Critic Verdict: {c2_verdict}")

        results.append({
            "id": b["id"],
            "drug": b["drug"],
            "elapsed_seconds": round(elapsed, 1),
            "formulator_r1": clean_f1,
            "critic_r1": clean_c1,
            "critic_r1_verdict": c1_verdict,
            "formulator_r2": clean_f2,
            "critic_r2": clean_c2,
            "critic_r2_verdict": c2_verdict
        })

    with open(r"C:\Users\mail4you0123\PharmaTerminal\benchmark_3_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nAll 3 benchmarks completed and saved to PharmaTerminal/benchmark_3_results.json")

if __name__ == "__main__":
    run_3_benchmarks()
