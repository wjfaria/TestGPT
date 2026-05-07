from __future__ import annotations


def infer_license_status(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["fda", "ema", "ich", "cdc", "nice", "cnil", "edpb"]):
        return "public_agency_document"
    if any(x in t for x in ["creative commons", "cc-by", "open access"]):
        return "open_license"
    if any(x in t for x in ["all rights reserved", "subscription", "purchase"]):
        return "publisher_restricted"
    return "manual_review_required"
