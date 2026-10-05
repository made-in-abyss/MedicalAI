import time
import json
import re
import requests
from fda_iid_data import lookup_excipient

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

# --- MODE A: BCS Class II/IV Amorphous Solid Dispersion & Solubility Bypass ---
ASD_FORMULATOR_SYSTEM = """You are a Senior Formulation Chemist specializing in Amorphous Solid Dispersions (ASD) and solubility enhancement.
Deliver a concrete formulation matrix as a raw JSON object. No markdown fences.
JSON Schema:
{
  "drug": string,
  "drug_dose_mg": float,
  "carrier_polymer": string (e.g. "Copovidone (PVP-VA 64)"),
  "polymer_ratio": string (e.g. "1:2"),
  "carrier_mg": float,
  "surfactant": string (e.g. "Vitamin E TPGS" or "Polysorbate 80"),
  "surfactant_mg": float,
  "filler_mg": float,
  "total_mass_mg": float,
  "physical_state": "Amorphous Solid Dispersion",
  "patent_design_around": string (how it circumvents innovator crystalline claims)
}"""

ASD_CRITIC_SYSTEM = """You are a Senior FDA Pharmaceutical Reviewer auditing an Amorphous Solid Dispersion (ASD).
Audit the formulation concisely in bullet points.
Criteria:
1. Physical Stability: miscibility, moisture plasticization (Tg depression), and phase separation/recrystallization.
2. Intestinal Kinetics: supersaturation precipitation at duodenal pH 6.8 ("spring and parachute" effect).
3. Excipient Limits & Mass: swallowability (<=650 mg) and FDA IID compliance.
Conclude strictly with:
'VERDICT: CONCEDED' (only if the matrix is chemically viable and compliant)
or
'VERDICT: REJECTED' (explain specific failure modes)"""

# --- MODE B: High-Dose Oral Direct Compression & Wet Granulation Tableting ---
TABLET_FORMULATOR_SYSTEM = """You are a Senior Industrial Pharmacist specializing in High-Dose Solid Oral Dosage Forms.
Deliver a concrete tableting recipe as a raw JSON object. No markdown fences.
JSON Schema:
{
  "drug": string,
  "drug_dose_mg": float,
  "binder": string (e.g. "Povidone (PVP K30)" at 3-5% w/w),
  "binder_mg": float,
  "disintegrant": string (e.g. "Croscarmellose Sodium" at 2-4% w/w),
  "disintegrant_mg": float,
  "lubricant": string (e.g. "Magnesium Stearate" at 0.5-1% w/w),
  "lubricant_mg": float,
  "filler": string (e.g. "Microcrystalline Cellulose (MCC PH-102)"),
  "filler_mg": float,
  "total_mass_mg": float,
  "manufacturing_process": string ("Direct Compression" or "Wet Granulation"),
  "capping_solution": string (how this prevents capping and punch sticking)
}"""

TABLET_CRITIC_SYSTEM = """You are a Senior Industrial Pharmacist & FDA Manufacturing Reviewer auditing a High-Dose Tablet.
Audit the formulation concisely in bullet points.
Criteria:
1. Tablet Physics: capping, lamination, and elastic recovery under high-speed compression.
2. Tooling & Flow: punch face sticking (adequate lubricant 0.5-1%) and powder flowability.
3. Disintegration & Mass: rapid disintegration (<15 min) and swallowability ceiling (<=650 mg).
DO NOT discuss amorphous phase separation or Tg depression—this is a crystalline tablet.
Conclude strictly with:
'VERDICT: CONCEDED' (only if tableting physics and mass are viable)
or
'VERDICT: REJECTED' (explain specific failure modes)"""

def query_ai(prompt, system_prompt, temp=0.15):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": system_prompt,
        "stream": True,
        "options": {
            "temperature": temp,
            "top_p": 0.9,
            "num_predict": 450,
            "num_ctx": 4096
        }
    }
    res = requests.post(OLLAMA_API, json=payload, stream=True, timeout=300)
    full_text = ""
    for line in res.iter_lines():
        if line:
            chunk = json.loads(line.decode("utf-8"))
            full_text += chunk.get("response", "")
    return full_text.strip()

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None

def silent_math_audit(form_dict, mode):
    """Silent, invisible Python math referee that calculates exact physical mass and checks FDA IID."""
    notes = []
    
    if mode == "tablet":
        dose = float(form_dict.get("drug_dose_mg", 0))
        binder = float(form_dict.get("binder_mg", 0))
        disint = float(form_dict.get("disintegrant_mg", 0))
        lub = float(form_dict.get("lubricant_mg", 0))
        filler = float(form_dict.get("filler_mg", 0))
        declared = float(form_dict.get("total_mass_mg", 0))
        
        actual_mass = round(dose + binder + disint + lub + filler, 1)
        
        # Check math honesty
        if abs(actual_mass - declared) > 15:
            notes.append(f"ARITHMETIC ERROR: Declared mass is {declared} mg, but component sum is {actual_mass} mg.")
        
        # Check swallowability ceiling
        if actual_mass > 700:
            notes.append(f"MASS BURDEN FATAL: Actual tablet mass {actual_mass} mg exceeds 700 mg swallowability limit.")
            
        # Check lubricant presence
        if lub <= 0 or not form_dict.get("lubricant"):
            notes.append("TOOLING FATAL: Missing lubricant (Magnesium Stearate / SSF); high risk of severe punch sticking.")
        elif lub > (actual_mass * 0.02):
            notes.append("LUBRICANT OVERLOAD: Lubricant >2% w/w causes hydrophobic tablet waterproofing and dissolution failure.")

        # Check binder ratio
        if binder > (actual_mass * 0.10):
            notes.append(f"BINDER OVERLOAD: Binder ({binder} mg) exceeds 10% w/w; forms gummy mass that retards disintegration.")

    elif mode == "asd":
        dose = float(form_dict.get("drug_dose_mg", 0))
        carrier = float(form_dict.get("carrier_mg", 0))
        surfactant = float(form_dict.get("surfactant_mg", 0))
        filler = float(form_dict.get("filler_mg", 0))
        declared = float(form_dict.get("total_mass_mg", 0))
        
        # If carrier_mg was omitted but ratio given
        if carrier == 0 and "polymer_ratio" in form_dict:
            try:
                r_str = str(form_dict["polymer_ratio"])
                parts = r_str.split(":")
                carrier = dose * (float(parts[1]) / float(parts[0]))
            except Exception:
                carrier = dose * 2.0
                
        actual_mass = round(dose + carrier + surfactant + filler, 1)
        
        if abs(actual_mass - declared) > 15:
            notes.append(f"ARITHMETIC ERROR: Declared mass is {declared} mg, but component sum is {actual_mass} mg.")
            
        if actual_mass > 700:
            notes.append(f"MASS BURDEN FATAL: Unit mass {actual_mass} mg exceeds patient swallowability limit (700 mg).")
            
        # Check FDA IID limits
        polymer_name = form_dict.get("carrier_polymer", "")
        if polymer_name:
            _, iid = lookup_excipient(polymer_name)
            if iid and carrier > iid["max_potency_mg"]:
                notes.append(f"FDA IID VIOLATION: {polymer_name} ({carrier} mg) exceeds CDER oral limit ({iid['max_potency_mg']} mg).")

    return {
        "actual_mass": actual_mass,
        "notes": notes
    }

def run_benchmark_scenario(name, mode, scenario_text):
    print("=" * 70, flush=True)
    print(f"BENCHMARK: {name} [Mode: {mode.upper()}]", flush=True)
    print("=" * 70, flush=True)
    t0 = time.time()
    
    form_sys = TABLET_FORMULATOR_SYSTEM if mode == "tablet" else ASD_FORMULATOR_SYSTEM
    critic_sys = TABLET_CRITIC_SYSTEM if mode == "tablet" else ASD_CRITIC_SYSTEM
    
    # Round 1: Formulator Pitch
    print("\n[*] 1. Formulator generating formulation matrix...", flush=True)
    pitch_prompt = f"Target Scenario:\n{scenario_text}\n\nDesign a concrete formulation in valid JSON."
    raw_pitch = query_ai(pitch_prompt, form_sys, temp=0.15)
    f1_json = extract_json(raw_pitch) or {}
    print(json.dumps(f1_json, indent=2), flush=True)
    
    # Silent Python Math & Reality Audit
    audit_r1 = silent_math_audit(f1_json, mode)
    math_note = ""
    if audit_r1["notes"]:
        math_note = "\n\n[INDEPENDENT PHYSICAL VERIFICATION NOTE]:\n" + "\n".join(f"- {n}" for n in audit_r1["notes"])
    
    # Round 1: Critic Challenge
    print("\n[*] 2. Red Team Critic auditing proposal...", flush=True)
    critic_prompt = f"""Target Scenario:
{scenario_text}

Proposed Formulation:
{json.dumps(f1_json, indent=2)}{math_note}

Audit this proposal directly. Be critical and rigorous. Conclude with VERDICT: CONCEDED or VERDICT: REJECTED."""

    critique_r1 = query_ai(critic_prompt, critic_sys, temp=0.05)
    print(critique_r1, flush=True)
    
    # Round 2: Formulator Defense & Revision
    print("\n[*] 3. Formulator revising matrix to fix objections...", flush=True)
    defense_prompt = f"""Target Scenario:
{scenario_text}

Your Previous Formulation:
{json.dumps(f1_json, indent=2)}

Critic Objections:
{critique_r1}

Revise your formulation matrix to resolve every objection. Ensure all component milligrams accurately sum to the declared total mass. Return raw JSON only."""

    raw_defense = query_ai(defense_prompt, form_sys, temp=0.15)
    f2_json = extract_json(raw_defense) or f1_json
    print(json.dumps(f2_json, indent=2), flush=True)
    
    # Silent Python Math & Reality Audit (Round 2)
    audit_r2 = silent_math_audit(f2_json, mode)
    math_note_r2 = ""
    if audit_r2["notes"]:
        math_note_r2 = "\n\n[INDEPENDENT PHYSICAL VERIFICATION NOTE]:\n" + "\n".join(f"- {n}" for n in audit_r2["notes"])

    # Round 2: Critic Final Verdict
    print("\n[*] 4. Red Team Critic rendering final verdict...", flush=True)
    final_critic_prompt = f"""Target Scenario:
{scenario_text}

Revised Formulation:
{json.dumps(f2_json, indent=2)}{math_note_r2}

Evaluate if all previous flaws were resolved. Conclude strictly with VERDICT: CONCEDED or VERDICT: REJECTED."""

    critique_r2 = query_ai(final_critic_prompt, critic_sys, temp=0.05)
    print(critique_r2, flush=True)
    
    verdict = "CONCEDED" if "VERDICT: CONCEDED" in critique_r2 else "REJECTED"
    elapsed = round(time.time() - t0, 1)
    print(f"\n>>> Scenario Finished in {elapsed}s | Verdict: {verdict}", flush=True)
    
    return {
        "drug": name,
        "mode": mode,
        "elapsed_s": elapsed,
        "f1": f1_json,
        "math_r1": audit_r1,
        "c1": critique_r1,
        "f2": f2_json,
        "math_r2": audit_r2,
        "c2": critique_r2,
        "verdict": verdict
    }

def main():
    benchmarks = [
        {
            "name": "Paracetamol (Acetaminophen) 500 mg",
            "mode": "tablet",
            "scenario": "Paracetamol 500 mg immediate-release oral tablet. Severe tableting capping and lamination due to monoclinic Form I elastic recovery. Tooling sticking risk. High unit dose (500 mg) requires >=75% drug load to maintain total tablet mass <= 650 mg."
        },
        {
            "name": "Ibrutinib (Imbruvica) 140 mg",
            "mode": "asd",
            "scenario": "Ibrutinib 140 mg oral dose. BCS Class II insolubility (<0.003 mg/mL at neutral pH 6.8). High food effect (AUC doubles with meals). Innovator patent claims crystalline Form A. Objective: Design an amorphous solid dispersion (ASD) bypassing Form A that maintains unit mass <= 500 mg."
        }
    ]
    
    all_results = []
    for b in benchmarks:
        res = run_benchmark_scenario(b["name"], b["mode"], b["scenario"])
        all_results.append(res)
        
    with open(r"C:\Users\mail4you0123\PharmaTerminal\hybrid_benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
        
    print("\n" + "=" * 70)
    print("ALL BENCHMARKS COMPLETE! Results saved to hybrid_benchmark_results.json")
    print("=" * 70)

if __name__ == "__main__":
    main()
