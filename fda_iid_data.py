# FDA Inactive Ingredient Database (IID) Reference for Oral & Injectable Delivery
# Reference: FDA Center for Drug Evaluation and Research (CDER) IID Records

FDA_IID_DATABASE = {
    "copovidone": {
        "aliases": ["pvp-va", "pvp/va", "kollidon va 64", "plasdone s-630", "copovidone"],
        "route": "ORAL",
        "max_potency_mg": 550.0,
        "function": "Amorphous Solid Dispersion Polymer"
    },
    "hpmc-as": {
        "aliases": ["hypromellose acetate succinate", "hpmcas", "aqoat", "hpmc-as"],
        "route": "ORAL",
        "max_potency_mg": 450.0,
        "function": "Enteric Solid Dispersion Polymer"
    },
    "povidone": {
        "aliases": ["pvp", "pvp k30", "pvp k25", "pvp k90", "povidone"],
        "route": "ORAL",
        "max_potency_mg": 250.0,
        "function": "Binder / Hydrophilic Carrier"
    },
    "soluplus": {
        "aliases": ["soluplus", "polyvinyl caprolactam"],
        "route": "ORAL",
        "max_potency_mg": 120.0,
        "function": "Polymeric Solubilizer"
    },
    "eudragit l100-55": {
        "aliases": ["eudragit", "eudragit l-100", "eudragit l100-55", "methacrylic acid copolymer"],
        "route": "ORAL",
        "max_potency_mg": 200.0,
        "function": "Enteric Release Matrix"
    },
    "polysorbate 80": {
        "aliases": ["tween 80", "polysorbate 80"],
        "route": "ORAL",
        "max_potency_mg": 150.0,
        "function": "Non-ionic Surfactant"
    },
    "sodium lauryl sulfate": {
        "aliases": ["sls", "sds", "sodium dodecyl sulfate", "sodium lauryl sulfate"],
        "route": "ORAL",
        "max_potency_mg": 51.5,
        "function": "Anionic Surfactant"
    },
    "capmul mcm": {
        "aliases": ["capmul", "capmul mcm", "glyceryl caprylate"],
        "route": "ORAL",
        "max_potency_mg": 350.0,
        "function": "Lipid Monoglyceride / SEDDS"
    },
    "labrasol": {
        "aliases": ["labrasol", "caprylocaproyl polyoxyl-8 glycerides"],
        "route": "ORAL",
        "max_potency_mg": 480.0,
        "function": "Lipid Surfactant / SEDDS"
    },
    "vitamin e tpgs": {
        "aliases": ["tpgs", "tocophersolan", "vitamin e tpgs"],
        "route": "ORAL",
        "max_potency_mg": 250.0,
        "function": "P-gp Inhibitor / Solubilizer"
    },
    "cremophor el": {
        "aliases": ["cremophor", "cremophor el", "kolliphor el", "polyoxyl 35 castor oil"],
        "route": "INJECTION",
        "max_potency_mg": 500.0,
        "function": "TOXIC SURFACTANT (Hypersensitivity & Peripheral Neuropathy warning)"
    },
    "peg 400": {
        "aliases": ["peg 400", "polyethylene glycol 400"],
        "route": "ORAL",
        "max_potency_mg": 600.0,
        "function": "Hydrophilic Co-solvent"
    }
}

def lookup_excipient(name):
    clean = name.lower().strip()
    for key, data in FDA_IID_DATABASE.items():
        if key in clean or any(alias in clean for alias in data["aliases"]):
            return key, data
    return None, None
