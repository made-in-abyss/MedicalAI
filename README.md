# MedicalAI (PharmaTerminal)

An autonomous dual-agent AI system for pharmaceutical formulation engineering, regulatory compliance auditing, and physical feasibility verification.

---

## Overview

MedicalAI is an engineering framework designed to assist pharmaceutical scientists in designing oral drug formulations while automatically enforcing strict physical and regulatory constraints.

In high-stakes pharmaceutical design, standard Large Language Models (LLMs) often suffer from two critical failure modes:
1. Arithmetic Inaccuracy: Models fail to sum multi-component masses accurately, often claiming compliance with tablet size limits when the actual ingredients exceed swallowability thresholds.
2. Unchecked Hallucination: Models readily invent compliant-sounding explanations that ignore real-world physical failure modes, such as tablet capping, tooling sticking, or phase separation.

MedicalAI solves this by pairing two specialized AI agents in an adversarial debate loop, supervised by a deterministic Python validation engine acting as an unyielding ground-truth referee.

---

## System Architecture

The pipeline consists of three core components:

```
[ User Input: Drug Name or Dose ]
              |
              v
+-------------------------------------------------------+
| 1. Auto-Enrichment & Mode Classifier                  |
|    - Maps drug to clinical dosage and solubility data |
|    - Selects Mode A (Solubility Enhancement) or       |
|      Mode B (High-Dose Solid Oral Dosage)             |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
| 2. Formulator Agent (Generator)                       |
|    - Proposes formulation composition and excipients   |
|    - Selects carrier ratios and manufacturing process |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
| 3. Deterministic Ground-Truth Referee (Python Engine) |
|    - Re-computes actual mass to catch math errors     |
|    - Audits against FDA Inactive Ingredient database  |
|    - Enforces maximum swallowability weight limits    |
|    - Injects hard physical facts into Critic prompt   |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
| 4. Red Team Critic Agent (Adversary)                  |
|    - Audits physical stability and tooling risks      |
|    - Evaluates compliance against regulatory ceilings |
|    - Issues specific objections or approval verdict   |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
| 5. Revision & Final Gatekeeper Loop                   |
|    - Formulator attempts to resolve all objections    |
|    - Final verdict rendered: APPROVED or REJECTED     |
+-------------------------------------------------------+
```

### Core Components

### 1. Formulator Agent
Acts as a formulation scientist. Given a drug molecule and clinical dose, the Formulator selects excipients (binders, disintegrants, lubricants, fillers, or polymer carriers), specifies mass ratios, and outputs a structured formulation matrix in JSON format.

### 2. Deterministic Ground-Truth Referee
A Python-based rule engine that runs silently between the agents. It:
- Sums the actual mass of all components to detect arithmetic errors.
- Cross-references proposed excipients against FDA Inactive Ingredient Database (IID) potency limits.
- Evaluates swallowability boundaries (e.g., maximum 700 mg for standard oral tablets).
- Injects factual constraints directly into the Critic's prompt, preventing the Formulator from hiding excess mass.

### 3. Red Team Critic Agent
Acts as an adversarial regulatory auditor. It critiques the formulation across multiple engineering dimensions:
- Physical Stability: Assesses risks of phase separation, moisture sensitivity, or crystalline transformation.
- Mechanical Feasibility: For tablets, audits compression mechanics, punch face sticking, capping, and lamination.
- Regulatory Compliance: Checks ingredient exposure against maximum approved daily intakes.

---

## Dual Formulation Modes

The system automatically switches between two specialized engineering modes depending on the drug's properties:

### Mode A: Solubility Enhancement (ASD / Lipid Formulations)
Targeted at poorly soluble molecules (BCS Class II and IV drugs such as Ibrutinib or Fenofibrate).
- Focuses on polymer carriers (copovidone, hypromellose acetate succinate), surfactant solubilizers, and amorphous solid dispersion techniques.
- Audits drug-polymer miscibility, glass transition stability, and intestinal precipitation kinetics.

### Mode B: High-Dose Solid Oral Dosage (Direct Compression / Granulation)
Targeted at high-dose active ingredients (typically doses above 300 mg such as Paracetamol).
- Focuses on powder compressibility, tableting mechanics, binder/filler balance, and disintegration time.
- Audits punch sticking, friability, capping under high-speed compression, and overall tablet swallowability.

---

## Tech Stack

- Language: Python 3.10+
- Inference Engine: Ollama (Local LLM inference, fully private and offline-capable)
- Base Language Model: Qwen 2.5 7B Instruct (4-bit quantization, optimized for local VRAM footprints)
- Data Sources: Curated extracts from the FDA Inactive Ingredient Database (IID)
- CLI Framework: Interactive terminal interface with live streaming output

---

## Project Structure

```
MedicalAI/
├── pharma_cli.py               # Interactive CLI terminal for running formulations
├── pharma_validator.py         # Deterministic rule engine and safety auditor
├── fda_iid_data.py             # Reference database of FDA-approved excipient potencies
├── run_hybrid_benchmarks.py    # Automated benchmark suite testing both formulation modes
├── LAUNCH_TERMINAL.bat         # One-click Windows launcher script
├── requirements.txt            # Python package dependencies
├── .gitignore                  # Git exclusion rules for large model weights
└── README.md                   # System documentation
```

---

## Getting Started

### Prerequisites

1. Python 3.10 or higher.
2. Ollama installed and running locally:
   Download from [ollama.com](https://ollama.com).
3. Pull the recommended base model:
   ```bash
   ollama pull qwen2.5:7b
   ```

### Installation

Clone the repository and install the required dependencies:

```bash
git clone https://github.com/made-in-abyss/MedicalAI.git
cd MedicalAI
pip install -r requirements.txt
```

### Running the System

#### Interactive CLI Terminal
To launch the interactive session:

```bash
python pharma_cli.py
```

On Windows, you can also double-click `LAUNCH_TERMINAL.bat`.

Example commands inside the CLI:
```text
/debate paracetamol
/debate ibrutinib
/mode tablet
/mode asd
/model qwen2.5:7b
/exit
```

#### Automated Benchmarks
To run the automated verification benchmark on real drugs:

```bash
python run_hybrid_benchmarks.py
```

This executes a full dual-agent debate and validation cycle across both Mode A (Ibrutinib 140 mg) and Mode B (Paracetamol 500 mg), saving structured evaluation metrics to `hybrid_benchmark_results.json`.

---

## Benchmark Evaluation Results

The system was evaluated against two real-world active pharmaceutical ingredients to test both failure modes:

| Test Parameter | Benchmark 1: Paracetamol (500 mg) | Benchmark 2: Ibrutinib (140 mg) |
| :--- | :--- | :--- |
| Target Mode | Mode B: Solid Oral Tablet | Mode A: Solubility Enhancement (ASD) |
| Proposed Formulator Mass | Declared: 650.0 mg | Declared: 410.0 mg |
| Actual Component Mass | Real: 813.8 mg (Arithmetic discrepancy) | Real: 450.0 mg (Arithmetic discrepancy) |
| Physical & Mechanical Audit | Critic identified elastic recovery of Form I crystals and tablet capping risks. | Critic audited polymer-drug miscibility and precipitation at intestinal pH. |
| Ground-Truth Referee Check | Flagged that 813.8 mg exceeds the 700 mg swallowability limit. | Flagged arithmetic inconsistency between declared and sum mass. |
| Final Audit Verdict | REJECTED | REJECTED |

Key Takeaway: The system successfully acts as a strict regulatory gatekeeper. Rather than acting as a simple text generator, the system refuses to approve formulations that violate mass conservation or physical feasibility limits.

---

## License

This project is licensed under the MIT License.
