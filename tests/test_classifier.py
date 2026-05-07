from kaariva_reference_agent.classifier import Classifier


def test_classifier_rwe():
    c = Classifier()
    assert c.classify("FDA real-world registry framework") == "02_rwe_registry_guidance"


def test_classifier_unknown_goes_review():
    c = Classifier()
    assert c.classify("Unmapped bespoke item") == "99_human_review_required"
