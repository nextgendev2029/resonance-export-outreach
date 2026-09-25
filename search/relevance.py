"""
Deterministic Home Decor Buyer Relevance & Categorization Engine for Resonance.
Evaluates discovered companies against commercial wholesale, retail, and interior
decor signals. Preserves factual evidence reasons without fabricating purchasing intent.
"""

import re
from typing import Dict, Any, Tuple, Optional

# Commercial wholesale & trade signals
BUYER_SIGNALS = {
    "Importer": [r"\bimporter\b", r"\bimport\b", r"\bimports\b", r"\bglobal trade\b"],
    "Distributor": [r"\bdistributor\b", r"\bdistribution\b", r"\bsupply co\b", r"\bsuppliers?\b"],
    "Wholesaler": [r"\bwholesale\b", r"\bwholesalers?\b", r"\bb2b\b", r"\bbulk pricing\b", r"\btrade account\b"],
    "Home Decor Store": [r"\bhome decor\b", r"\bhome goods\b", r"\bdecor store\b", r"\binterior decor\b", r"\bdecorative\b"],
    "Gift Shop": [r"\bgift shop\b", r"\bgifts? store\b", r"\bgift boutique\b", r"\bsouvenir\b"],
    "Wellness Store": [r"\bwellness store\b", r"\bholistic\b", r"\bmeditation studio\b", r"\bsound healing\b", r"\byoga studio\b", r"\bmetaphysical\b"],
    "Interior Decor Business": [r"\binterior design\b", r"\binterior decorator\b", r"\bdesign studio\b", r"\bdesign firm\b"],
    "Lifestyle Store": [r"\blifestyle store\b", r"\blifestyle boutique\b", r"\bconcept store\b"],
    "Boutique Store": [r"\bboutique\b", r"\bcurated store\b", r"\bspecialty shop\b"],
    "Retailer": [r"\bretailer\b", r"\bretail store\b", r"\bshop\b", r"\bstorefront\b"],
    "Musical Instrument Retailer": [r"\bmusical instruments?\b", r"\bacoustic instruments?\b", r"\bsound instruments?\b", r"\bgong\b", r"\bpercussion\b"],
}

# Product category & niche signals
PRODUCT_SIGNALS = [
    r"\bsinging bowls?\b", r"\btibetan bowls?\b", r"\bsound therapy\b",
    r"\bhome decor\b", r"\binterior decor\b", r"\bdecorative accessories\b",
    r"\bartisan crafts\b", r"\bhandcrafted\b", r"\bhome goods\b",
    r"\bwellness goods\b", r"\bmeditation\b", r"\baromatherapy\b",
    r"\bacoustic\b", r"\bhand-hammered\b", r"\bbrass decor\b"
]

# Irrelevant or consumer-only negative signals
NEGATIVE_SIGNALS = [
    r"\bsoftware\b", r"\bsaas\b", r"\breal estate\b", r"\bmedical clinic\b",
    r"\bdental\b", r"\blaw firm\b", r"\baccounting\b", r"\bused cars?\b",
    r"\bpersonal blog\b", r"\bforum\b", r"\bwikipedia\b"
]


class HomeDecorRelevanceEvaluator:
    """Evaluates business relevance for Home Decor and Singing Bowls export outreach."""

    @classmethod
    def evaluate(
        cls,
        company_name: str = "",
        raw_text: str = "",
        website: str = "",
        query: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluate text context for Home Decor buyer fit.
        Returns:
            {
                "relevance": "High" | "Medium" | "Low" | "Unknown",
                "buyer_type": str,
                "relevance_reason": str,
                "matched_signals": List[str]
            }
        """
        combined = f"{company_name} {website} {raw_text} {query}".lower()
        matched_buyer_types = []
        matched_decor_signals = []
        matched_negatives = []

        # 1. Check for negative / non-trade indicators
        for neg in NEGATIVE_SIGNALS:
            if re.search(neg, combined):
                matched_negatives.append(neg.replace(r"\b", ""))

        # 2. Check for buyer type signals
        detected_primary_type = "Wholesaler"
        for b_type, patterns in BUYER_SIGNALS.items():
            for pat in patterns:
                if re.search(pat, combined):
                    if b_type not in matched_buyer_types:
                        matched_buyer_types.append(b_type)
                    break

        for preferred in ("Wholesaler", "Distributor", "Importer", "Home Decor Store", "Gift Shop", "Wellness Store", "Retailer", "Interior Decor Business", "Boutique Store", "Lifestyle Store", "Musical Instrument Retailer"):
            if preferred in matched_buyer_types:
                detected_primary_type = preferred
                break

        # 3. Check for product / decor signals
        for prod in PRODUCT_SIGNALS:
            if re.search(prod, combined):
                clean_prod = prod.replace(r"\b", "").replace(r"?", "")
                if clean_prod not in matched_decor_signals:
                    matched_decor_signals.append(clean_prod)

        # 4. Determine relevance score
        if matched_negatives and not matched_decor_signals:
            return {
                "relevance": "Low",
                "buyer_type": "Other",
                "relevance_reason": f"Non-trade or unrelated category detected: {', '.join(matched_negatives[:2])}",
                "matched_signals": matched_negatives
            }

        if matched_buyer_types and matched_decor_signals:
            buyer_list = ", ".join(matched_buyer_types[:3])
            decor_list = ", ".join(matched_decor_signals[:3])
            return {
                "relevance": "High",
                "buyer_type": detected_primary_type,
                "relevance_reason": f"Strong alignment: matched commercial buyer role ({buyer_list}) and decor/acoustic goods ({decor_list})",
                "matched_signals": matched_buyer_types + matched_decor_signals
            }

        if matched_buyer_types or matched_decor_signals:
            signals = matched_buyer_types if matched_buyer_types else matched_decor_signals
            return {
                "relevance": "Medium",
                "buyer_type": detected_primary_type if matched_buyer_types else "Home Decor Store",
                "relevance_reason": f"Plausible trade fit: matched category signals ({', '.join(signals[:3])})",
                "matched_signals": signals
            }

        return {
            "relevance": "Unknown",
            "buyer_type": "Wholesaler",
            "relevance_reason": "Insufficient public catalog or directory signals to establish decor commercial role",
            "matched_signals": []
        }
