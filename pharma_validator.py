import re
import json
from fda_iid_data import lookup_excipient

class FormulationValidator:
    """
    Automated Biochemical & Regulatory Rule Engine:
    1. Conservation of Mass & Tablet Swallowability Check.
    2. Ground-Truth FDA Inactive Ingredient Database (IID) Limits.
    3. Smart Negation-Aware Patent Claim Infringement Detection.
    """

    NEGATION_PREFIXES = r"(?:avoid|avoiding|avoids|without|free\s+of|circumvent|circumventing|circumvents|bypasses|bypassing|does\s+not\s+(?:use|contain|infringe)|replaces|replacing|instead\s+of|alternative\s+to|non-|no)"

    @classmethod
    def is_patent_infringement(cls, term, text_dump, recipe_fields=""):
        """
        Distinguishes between actual infringement vs. claiming to AVOID the patent.
        Returns True if infringed, False if safely avoided or not present.
        """
        escaped_term = re.escape(term.strip())
        
        # 1. Direct hit in primary recipe fields (carrier, physical state, polymer)
        if re.search(r"\b" + escaped_term + r"\b", recipe_fields, re.IGNORECASE):
            return True, "Directly specified in formulation matrix"

        # 2. Check in full text dump
        term_matches = list(re.finditer(r"\b" + escaped_term + r"\b", text_dump, re.IGNORECASE))
        if not term_matches:
            return False, "Not mentioned"

        # Check each occurrence for negation context within 45 characters prior
        for match in term_matches:
            start_pos = max(0, match.start() - 45)
            context_window = text_dump[start_pos:match.start()].lower()
            
            # If preceded by negation/avoidance word, it is a safe non-infringement claim
            if re.search(cls.NEGATION_PREFIXES, context_window):
                continue
            
            # Found an un-negated claim of the prohibited patent term
            return True, f"Found un-negated mention in formulation rationale: '...{context_window}{match.group(0)}...'"

        return False, "Explicitly stated as avoided/circumvented"

    @classmethod
    def audit_formulation(cls, formulation_dict, forbidden_terms=None):
        findings = []
        fatal_errors = []

        dose_mg = float(formulation_dict.get("drug_dose_mg", 0) or formulation_dict.get("dose_mg", 0) or 0)
        polymer = str(formulation_dict.get("carrier", "") or formulation_dict.get("polymer", ""))
        polymer_ratio = formulation_dict.get("polymer_ratio", 0) or formulation_dict.get("ratio", 0)
        surfactant = str(formulation_dict.get("surfactant", "") or formulation_dict.get("inhibitor", ""))
        surfactant_mg = float(formulation_dict.get("surfactant_mg", 0) or 0)
        declared_mass = float(formulation_dict.get("total_mass_mg", 0) or formulation_dict.get("mass_mg", 0) or 0)
        physical_state = str(formulation_dict.get("physical_state", ""))
        rationale = str(formulation_dict.get("patent_workaround", ""))

        # 1. Mass balance calculation
        try:
            if isinstance(polymer_ratio, str):
                if ":" in polymer_ratio:
                    parts = polymer_ratio.split(":")
                    ratio_num = float(parts[1]) / float(parts[0])
                else:
                    ratio_num = float(re.sub(r"[^\d.]", "", polymer_ratio))
            else:
                ratio_num = float(polymer_ratio)
        except Exception:
            ratio_num = 1.0

        expected_polymer_mass = dose_mg * ratio_num
        calculated_matrix_mass = dose_mg + expected_polymer_mass + surfactant_mg

        # Effective unit mass for swallowing assessment
        effective_mass = declared_mass if declared_mass > 0 else calculated_matrix_mass

        # Detect hallucinated filler overload
        if declared_mass > calculated_matrix_mass * 3 and declared_mass > 700:
            findings.append(
                f"[FILLER OVERLOAD NOTED] Formulator declared {declared_mass:.1f} mg, but active core is only {calculated_matrix_mass:.1f} mg. Matrix can be compacted to ~{calculated_matrix_mass * 1.3:.0f} mg."
            )
            # Re-evaluate effective swallowing on realistic compacted tablet
            effective_mass = calculated_matrix_mass * 1.3

        # Check patient swallowability ceiling (FDA oral standard ~750 mg)
        if effective_mass > 750:
            fatal_errors.append(
                f"[MASS BURDEN EXCEEDED] Calculated tablet mass {effective_mass:.1f} mg exceeds FDA patient swallowability ceiling (750 mg). Pill is too large."
            )
        elif effective_mass > 550:
            findings.append(
                f"[HIGH MASS WARNING] Unit mass {effective_mass:.1f} mg is near capsule threshold. Acceptable, but compacting recommended."
            )
        else:
            findings.append(
                f"[MASS OK] Effective unit mass {effective_mass:.1f} mg is easily swallowable (Active: {dose_mg:.0f}mg, Polymer: {expected_polymer_mass:.0f}mg)."
            )

        # 2. Excipient FDA IID Verification
        if polymer:
            key, iid = lookup_excipient(polymer)
            if iid:
                if expected_polymer_mass > iid["max_potency_mg"]:
                    fatal_errors.append(
                        f"[FDA IID VIOLATION] Proposed {polymer} mass ({expected_polymer_mass:.1f} mg) exceeds FDA Inactive Ingredient Database limit ({iid['max_potency_mg']:.1f} mg for {iid['route']})."
                    )
                else:
                    findings.append(
                        f"[FDA IID COMPLIANT] {polymer} ({expected_polymer_mass:.1f} mg) within FDA IID cap ({iid['max_potency_mg']:.1f} mg)."
                    )
            else:
                findings.append(f"[IID UNINDEXED] Polymer '{polymer}' not found in standard CDER lookup.")

        if surfactant and surfactant_mg > 0:
            key, iid = lookup_excipient(surfactant)
            if iid:
                if surfactant_mg > iid["max_potency_mg"]:
                    fatal_errors.append(
                        f"[FDA IID VIOLATION] Surfactant {surfactant} ({surfactant_mg:.1f} mg) exceeds FDA IID limit ({iid['max_potency_mg']:.1f} mg)."
                    )
                else:
                    findings.append(
                        f"[FDA IID COMPLIANT] Surfactant {surfactant} ({surfactant_mg:.1f} mg) within FDA IID cap ({iid['max_potency_mg']:.1f} mg)."
                    )

        # 3. Smart Negation-Aware Patent Claim Audit
        recipe_concat = f"{polymer} {physical_state} {surfactant}"
        full_text = json.dumps(formulation_dict)

        if forbidden_terms:
            for term in forbidden_terms:
                is_infringing, detail = cls.is_patent_infringement(term, full_text, recipe_concat)
                if is_infringing:
                    fatal_errors.append(
                        f"[PATENT INFRINGEMENT RISK] Prohibited innovator claim '{term}': {detail}"
                    )
                else:
                    findings.append(
                        f"[PATENT WORKAROUND VERIFIED] Prohibited claim '{term}' is successfully avoided ({detail})."
                    )

        return {
            "is_valid": len(fatal_errors) == 0,
            "fatal_errors": fatal_errors,
            "findings": findings,
            "calculated_mass_mg": round(calculated_matrix_mass, 1),
            "calculated_core_mass_mg": round(calculated_matrix_mass, 1),
            "effective_unit_mass_mg": round(effective_mass, 1)
        }
