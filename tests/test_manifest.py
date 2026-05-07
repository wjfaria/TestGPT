from datetime import date

from kaariva_reference_agent.schemas import ManifestRecord


def test_manifest_record_schema():
    rec = ManifestRecord(
        document_id="X",
        title="Y",
        issuer="Z",
        jurisdiction="EU",
        document_type="Guidance",
        source_url="https://fda.gov/a.pdf",
        access_status="public",
        license_status="public_agency_document",
        download_allowed=True,
        retrieved_date=date.today(),
        file_format="pdf",
        local_path="documents/01_core_clinical_research_governance/a.pdf",
        checksum_sha256="abc",
        classification="01_core_clinical_research_governance",
        relevance_to_kaariva="test",
        use_in_rag=False,
        human_review_required=True,
    )
    assert rec.document_id == "X"
