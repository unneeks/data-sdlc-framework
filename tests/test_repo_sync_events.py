"""Unit tests for the SDLC event envelope (domain/events.py) — round-trip
serialization and the "at least one document" validation the
DOCUMENT_PUBLISHED payload enforces.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

import pytest

from domain.events import (
    CodePushedToS3Payload,
    DocumentDescriptor,
    DocumentPublishedPayload,
    SDLCEventType,
    SdlcEventEnvelope,
)


def test_code_pushed_envelope_round_trips():
    envelope = SdlcEventEnvelope(
        event_type=SDLCEventType.CODE_PUSHED_TO_S3,
        project_key="data-sdlc-framework",
        session_id="s1",
        agent_id="a1",
        payload=CodePushedToS3Payload(
            bucket="b", code_prefix="repo-sync/code", tarball_key="k.tar.gz",
            branch_name="agentcore/a1/s1", commit_sha="abc123", base_commit_sha="base123",
            session_id="s1", agent_id="a1", files_changed=3,
        ),
    )

    raw = envelope.model_dump_json()
    restored = SdlcEventEnvelope.model_validate_json(raw)

    assert restored.event_type == SDLCEventType.CODE_PUSHED_TO_S3
    assert isinstance(restored.payload, CodePushedToS3Payload)
    assert restored.payload.commit_sha == "abc123"
    assert restored.payload.files_changed == 3


def test_document_published_envelope_round_trips():
    envelope = SdlcEventEnvelope(
        event_type=SDLCEventType.DOCUMENT_PUBLISHED,
        project_key="data-sdlc-framework",
        session_id="s1",
        agent_id="a1",
        payload=DocumentPublishedPayload(
            session_id="s1", agent_id="a1",
            documents=[
                DocumentDescriptor(name="spec.md", s3_key="docs/s1/x/spec.md", bucket="b"),
                DocumentDescriptor(name="plan.md", s3_key="docs/s1/y/plan.md", bucket="b"),
            ],
        ),
    )

    restored = SdlcEventEnvelope.model_validate_json(envelope.model_dump_json())

    assert restored.event_type == SDLCEventType.DOCUMENT_PUBLISHED
    assert isinstance(restored.payload, DocumentPublishedPayload)
    assert len(restored.payload.documents) == 2
    assert restored.payload.documents[0].name == "spec.md"


def test_document_published_payload_requires_at_least_one_document():
    with pytest.raises(Exception):
        DocumentPublishedPayload(session_id="s1", agent_id="a1", documents=[])


def test_schema_version_defaults_to_one():
    envelope = SdlcEventEnvelope(
        event_type=SDLCEventType.CODE_PUSHED_TO_S3,
        project_key="p", session_id="s", agent_id="a",
        payload=CodePushedToS3Payload(
            bucket="b", code_prefix="c", tarball_key="k", branch_name="br",
            commit_sha="x", base_commit_sha="y", session_id="s", agent_id="a",
        ),
    )
    assert envelope.schema_version == "1"


if __name__ == "__main__":
    test_code_pushed_envelope_round_trips()
    test_document_published_envelope_round_trips()
    test_document_published_payload_requires_at_least_one_document()
    test_schema_version_defaults_to_one()
    print("All repo-sync event envelope tests passed successfully!")
