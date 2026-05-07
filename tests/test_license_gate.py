from kaariva_reference_agent.license_gate import infer_license_status


def test_license_open_access():
    assert infer_license_status("This article is open access under CC-BY") == "open_license"


def test_license_unknown():
    assert infer_license_status("No signals") == "manual_review_required"
