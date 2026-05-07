from kaariva_reference_agent.allowlist import Allowlist


def test_allowlist_allows_subdomain():
    allow = Allowlist()
    assert allow.is_allowed("https://sub.fda.gov/guidance")


def test_allowlist_rejects_unknown():
    allow = Allowlist()
    assert not allow.is_allowed("https://example.com/file.pdf")
