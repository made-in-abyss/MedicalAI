import os
import sys
import json
import time
import re
import requests

# ANSI Color Codes for Hacker/Terminal Aesthetic
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

OLLAMA_API = "http://localhost:11434/api"

# Clean, Professional Personas
FORMULATOR_SYSTEM = """You are a Senior Pharmaceutical Formulation Chemist.
Deliver a concrete formulation matrix as a valid JSON object. No markdown fences, no conversational filler.
JSON Schema:
{
  "drug": string,
  "drug_dose_mg": float,
  "carrier": string (e.g. "Copovidone (PVP-VA 64)", "Povidone (PVP K30)", "Pregelatinized Starch"),
  "polymer_ratio": string (e.g. "1:2" or "1:0.1"),
  "functional_excipients": string (e.g. disintegrant, lubricant, surfactant),
  "excipient_mg": float,
  "total_mass_mg": float,
  "physical_state": string ("Amorphous Solid Dispersion", "Immediate-Release Tablet", or "SEDDS"),
  "design_rationale": string (2 sentences on how this solves the formulation/patent barrier)
}"""

CRITIC_SYSTEM = """You are a Senior Pharmaceutical Toxicologist and FDA Reviewer.
Audit the proposed formulation directly, ruthlessly, and concisely. Output bullet points and verdict only.
Audit Criteria:
1. Physical & Chemical Stability: phase separation, moisture plasticization (Tg depression), recrystallization, or acid degradation.
2. Tableting & Manufacturability: capping, lamination, punch sticking (lubrication), or excessive mass burden (>650 mg).
3. Dissolution & Pharmacokinetics: intestinal precipitation (pH 6.8), food effect, or delayed release.

Conclude strictly with:
'VERDICT: CONCEDED' (only if the design is chemically viable and compliant)
or
'VERDICT: REJECTED' (highlight the fatal flaws)"""

# Built-in pharmacological profiles for one-word inputs
BUILTIN_DRUG_PROFILES = {
    "paracetamol": {
        "name": "Paracetamol (Acetaminophen)",
        "scenario": "Paracetamol (500 mg oral tablet). Severe compressibility & capping challenges (monoclinic Form I elastic recovery). High unit dose requires >=75% drug load to maintain total tablet mass <= 650 mg. Bitter taste."
    },
    "acetaminophen": {
        "name": "Acetaminophen (Paracetamol)",
        "scenario": "Acetaminophen (500 mg oral tablet). Severe compressibility & capping challenges (monoclinic Form I elastic recovery). High unit dose requires >=75% drug load to maintain total tablet mass <= 650 mg. Bitter taste."
    },
    "oseltamivir": {
        "name": "Oseltamivir (Tamiflu)",
        "scenario": "Oseltamivir Phosphate (75 mg oral dose). Severe pediatric vomiting, extreme bitter taste, and liquid suspension degradation requiring refrigeration. Design a stable, taste-masked room-temperature formulation."
    },
    "tamiflu": {
        "name": "Tamiflu (Oseltamivir)",
        "scenario": "Oseltamivir Phosphate (75 mg oral dose). Severe pediatric vomiting, extreme bitter taste, and liquid suspension degradation requiring refrigeration. Design a stable, taste-masked room-temperature formulation."
    },
    "ibuprofen": {
        "name": "Ibuprofen",
        "scenario": "Ibuprofen (400 mg oral tablet). Low melting point (75-77°C) causes punch face sticking and tooling filming. Hydrophobic, high dose."
    },
    "aspirin": {
        "name": "Aspirin (Acetylsalicylic Acid)",
        "scenario": "Aspirin (500 mg oral tablet). Moisture-sensitive hydrolysis degradation to salicylic acid. High gastric irritation."
    },
    "ibrutinib": {
        "name": "Ibrutinib (Imbruvica)",
        "scenario": "Ibrutinib (140 mg oral dose). BCS Class II extreme insolubility (<0.003 mg/mL at pH 6.8). High food effect. Innovator holds crystalline Form A claims."
    },
    "apalutamide": {
        "name": "Apalutamide (Erleada)",
        "scenario": "Apalutamide (60 mg oral dose). BCS Class II insolubility. Severe pill burden (4 tablets daily). Innovator claims spray-dried HPMC-AS 1:3 ratio."
    },
    "paclitaxel": {
        "name": "Paclitaxel (Taxol/Abraxane)",
        "scenario": "Paclitaxel IV infusion. Highly hydrophobic. Eliminate toxic Cremophor EL solvent. Avoid patented albumin nanoparticles (Abraxane)."
    }
}

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    banner = f"""{CYAN}{BOLD}
    ██████╗ ██╗  ██╗ █████╗ ██████╗ ███╗   ███╗ █████╗ 
    ██╔══██╗██║  ██║██╔══██╗██╔══██╗████╗ ████║██╔══██╗
    ██████╔╝███████║███████║██████╔╝██╔████╔██║███████║
    ██╔═══╝ ██╔══██║██╔══██║██╔══██╗██║╚██╔╝██║██╔══██║
    ██║     ██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║██║  ██║
    ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝
    {MAGENTA}>> AUTONOMOUS PHARMACOLOGICAL DEBATE TERMINAL <<{RESET}
    {DIM}Pure Adversarial Engine: Formulator vs. Red Team Critic{RESET}
    """
    print(banner)

def get_installed_models():
    """Fetch all installed models in Ollama."""
    models = []
    try:
        res = requests.get(f"{OLLAMA_API}/tags", timeout=3)
        if res.status_code == 200:
            for m in res.json().get("models", []):
                models.append(m.get("name"))
    except Exception:
        pass
    return models

def query_model(prompt, model, system_prompt=None, temp=0.2, stream=False):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": temp,
            "top_p": 0.9,
            "num_predict": 450
        }
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        if not stream:
            res = requests.post(f"{OLLAMA_API}/generate", json=payload, timeout=90).json()
            return res.get("response", "").strip()
        
        res = requests.post(f"{OLLAMA_API}/generate", json=payload, stream=True, timeout=120)
        full_text = ""
        for line in res.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                token = chunk.get("response", "")
                full_text += token
                sys.stdout.write(f"{GREEN}{token}{RESET}")
                sys.stdout.flush()
        print()
        return full_text
    except Exception as e:
        print(f"\n{RED}[!] Error querying local model: {e}{RESET}")
        return ""

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None

def resolve_drug_scenario(user_input, model):
    """Enriches a simple drug name into a full formulation scenario."""
    clean_input = user_input.strip().lower()
    
    # Check built-in profiles
    for key, profile in BUILTIN_DRUG_PROFILES.items():
        if key in clean_input:
            print(f"{GREEN}[✓] Target Identified:{RESET} {BOLD}{profile['name']}{RESET}")
            return profile["scenario"]

    # If it's already a full multi-word scenario (e.g. > 6 words), use as is
    if len(clean_input.split()) > 6:
        return user_input

    # Dynamic 2-second AI auto-enrichment for any unlisted drug name
    print(f"{YELLOW}[*] Resolving clinical dose & delivery profile for '{user_input}'...{RESET}")
    enrich_prompt = f"Identify standard oral clinical dose (mg), BCS class, and key tableting/solubility challenge for: {user_input}. Output ONLY a 1-sentence formulation scenario."
    scenario = query_model(enrich_prompt, model, temp=0.1, stream=False)
    if not scenario:
        scenario = f"Target: {user_input} oral dosage form. Optimize dissolution, stability, and patient swallowability."
    print(f"{CYAN}ℹ Scenario:{RESET} {scenario}\n")
    return scenario

def run_adversarial_debate(model, target_problem, max_rounds=2):
    """Executes a clean, unpolluted debate passing raw arguments between Formulator and Critic."""
    print(f"\n{CYAN}{BOLD}{'='*70}\n[ARENA]: INITIATING ADVERSARIAL DEBATE\nTarget: {target_problem}\n{'='*70}{RESET}\n")

    # Round 1: Formulator Proposal
    print(f"{CYAN}{BOLD}🧪 [FORMULATOR]: Pitching Formulation Blueprint...{RESET}")
    pitch_prompt = f"Target Scenario:\n{target_problem}\n\nDesign a concrete formulation matrix in clean JSON."
    raw_pitch = query_model(pitch_prompt, model, FORMULATOR_SYSTEM, temp=0.2, stream=False)
    form_json = extract_json(raw_pitch)

    if form_json:
        current_proposal_text = json.dumps(form_json, indent=2)
    else:
        current_proposal_text = raw_pitch

    print(f"{GREEN}{current_proposal_text}{RESET}\n")

    for r in range(1, max_rounds + 1):
        print(f"{MAGENTA}{BOLD}{'─'*28} ROUND {r} AUDIT {'─'*28}{RESET}")
        
        # Critic Challenge (Direct pass, zero Python clutter)
        print(f"{RED}{BOLD}⚖️ [RED TEAM CRITIC]: Challenging Formulation...{RESET}")
        critic_prompt = f"""Target Scenario:
{target_problem}

Proposed Formulation:
{current_proposal_text}

Audit this formulation critically for physical chemistry stability, tableting liabilities, excipient limits, and dissolution kinetics. Conclude with VERDICT: CONCEDED or VERDICT: REJECTED."""

        critique = query_model(critic_prompt, model, CRITIC_SYSTEM, temp=0.1, stream=True)

        if "VERDICT: CONCEDED" in critique:
            print(f"\n{GREEN}{BOLD}{'='*70}\n🏆 [STATUS: CONCEDED - FORMULATION VALIDATED!]\nRed Team Critic accepted the design.\n{'='*70}{RESET}")
            break

        if r == max_rounds:
            print(f"\n{YELLOW}{BOLD}{'='*70}\n⚠️ [STATUS: FINAL VERDICT - REJECTED]\nDebate closed after {max_rounds} rounds. Revision rejected by Critic.\n{'='*70}{RESET}")
            break

        # Formulator Counter-Defense / Revision
        print(f"\n{CYAN}{BOLD}🧪 [FORMULATOR]: Countering Objections & Revising Matrix...{RESET}")
        defense_prompt = f"""Target Scenario:
{target_problem}

Your Previous Formulation:
{current_proposal_text}

Critic Objections:
{critique}

Revise your formulation matrix to directly resolve every objection raised by the Critic. Return updated JSON only."""
        raw_rev = query_model(defense_prompt, model, FORMULATOR_SYSTEM, temp=0.2, stream=False)
        rev_json = extract_json(raw_rev)
        if rev_json:
            current_proposal_text = json.dumps(rev_json, indent=2)
        else:
            current_proposal_text = raw_rev
        print(f"{GREEN}{current_proposal_text}{RESET}\n")

def main():
    clear_screen()
    print_banner()

    models = get_installed_models()
    if not models:
        print(f"{RED}[!] No Ollama models found. Ensure Ollama is running.{RESET}")
        input("Press Enter to exit...")
        return

    # Default to the newly pulled Qwen 2.5 7B, then 3B
    current_model = "qwen2.5:7b" if "qwen2.5:7b" in models else ("qwen2.5:3b" if "qwen2.5:3b" in models else models[0])

    print(f"{GREEN}[✓] Engine Ready.{RESET} Active Model: {BOLD}{current_model}{RESET}")
    print(f"{DIM}Commands: /debate [drug_name] | /model (switch model) | /clear | /exit{RESET}\n")

    while True:
        try:
            user_input = input(f"{CYAN}{BOLD}pharma-cli [{current_model}]>{RESET} ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["/exit", "exit", "quit", ":q"]:
                print(f"{DIM}Exiting PharmaTerminal...{RESET}")
                break

            elif user_input.lower() == "/clear":
                clear_screen()
                print_banner()
                continue

            elif user_input.lower() == "/model":
                models = get_installed_models()
                print(f"\n{BOLD}Available Models:{RESET}")
                for i, m in enumerate(models, 1):
                    prefix = f"{GREEN}* " if m == current_model else "  "
                    tag = " [7B Instruct - High IQ]" if "7b" in m and "pharma" not in m and "r1" not in m else (" [3B - Ultra Fast]" if "3b" in m else "")
                    print(f"{prefix}[{i}] {m}{tag}{RESET}")
                choice = input(f"\nSelect model index (1-{len(models)}): ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(models):
                        current_model = models[idx]
                        print(f"{GREEN}[✓] Switched active model to: {current_model}{RESET}\n")
                except ValueError:
                    print(f"{RED}[!] Invalid choice.{RESET}\n")
                continue

            elif user_input.lower().startswith("/debate"):
                parts = user_input.split(maxsplit=1)
                
                # Direct command: /debate paracetamol
                if len(parts) > 1:
                    raw_drug = parts[1].strip()
                    scenario = resolve_drug_scenario(raw_drug, current_model)
                    run_adversarial_debate(current_model, scenario, max_rounds=2)
                    continue

                # Interactive menu
                print(f"\n{YELLOW}{BOLD}Select Target Drug for Debate:{RESET}")
                print("1. Oseltamivir / Tamiflu (Taste masking, pediatric liquid stability)")
                print("2. Paracetamol (High dose, tableting capping & compressibility)")
                print("3. Ibrutinib (BCS Class II, Form A patent, food effect)")
                print("4. Apalutamide (Pill burden reduction, HPMC-AS 1:3 bypass)")
                print("5. Custom / Any Drug Name (e.g. 'Ibuprofen', 'Metformin')")
                choice = input("\nChoice (1-5): ").strip()

                if choice == "1":
                    drug_key = "oseltamivir"
                elif choice == "2":
                    drug_key = "paracetamol"
                elif choice == "3":
                    drug_key = "ibrutinib"
                elif choice == "4":
                    drug_key = "apalutamide"
                elif choice == "5":
                    drug_key = input("\nEnter drug name or full scenario: ").strip()
                else:
                    print(f"{RED}[!] Invalid choice.{RESET}\n")
                    continue

                scenario = resolve_drug_scenario(drug_key, current_model)
                run_adversarial_debate(current_model, scenario, max_rounds=2)
                continue

            elif user_input.startswith("/"):
                print(f"{RED}[!] Unknown command. Available: /debate [drug], /model, /clear, /exit{RESET}\n")
                continue

            # If user just types a single drug name directly (e.g. 'oseltamivir' or 'paracetamol')
            clean_test = user_input.strip().lower()
            if clean_test in BUILTIN_DRUG_PROFILES or len(clean_test.split()) == 1:
                scenario = resolve_drug_scenario(user_input, current_model)
                run_adversarial_debate(current_model, scenario, max_rounds=2)
                continue

            # Standard Research Query Mode
            print(f"\n{GREEN}{BOLD}AI Assistant:{RESET}")
            query_model(user_input, current_model, temp=0.2, stream=True)
            print()

        except KeyboardInterrupt:
            print(f"\n{DIM}Session interrupted. Type /exit to quit.{RESET}\n")
        except Exception as e:
            print(f"\n{RED}[!] Unexpected error: {e}{RESET}\n")

if __name__ == "__main__":
    main()
