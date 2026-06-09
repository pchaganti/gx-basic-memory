from scripts import bm_bossbot_status


def test_status_script_is_uv_typer_entrypoint() -> None:
    source = bm_bossbot_status.__file__
    assert source is not None
    text = open(source, encoding="utf-8").read()

    assert text.startswith("#!/usr/bin/env -S uv run --script\n")
    assert "# /// script" in text
    assert "typer" in text
    assert hasattr(bm_bossbot_status, "app")


def _review_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "reviewed_head_sha": "abc123",
        "review_complete": True,
        "verdict": "approve",
        "blocking_findings": [],
        "nonblocking_findings": [],
        "summary": "The change is ready.",
    }
    payload.update(overrides)
    return payload


def test_validate_review_accepts_matching_approved_head_sha() -> None:
    result = bm_bossbot_status.validate_review(_review_payload(), expected_head_sha="abc123")

    assert result.approved is True
    assert result.state == "success"
    assert result.description == "BM Bossbot approved this head SHA"


def test_validate_review_rejects_stale_head_sha() -> None:
    result = bm_bossbot_status.validate_review(_review_payload(), expected_head_sha="def456")

    assert result.approved is False
    assert result.state == "failure"
    assert result.description == "BM Bossbot reviewed a stale head SHA"


def test_validate_review_rejects_blocking_findings() -> None:
    result = bm_bossbot_status.validate_review(
        _review_payload(blocking_findings=[{"title": "Missing test", "body": "Add coverage."}]),
        expected_head_sha="abc123",
    )

    assert result.approved is False
    assert result.state == "failure"
    assert result.description == "BM Bossbot requested changes"


def test_status_payload_uses_required_context() -> None:
    payload = bm_bossbot_status.build_status_payload(
        state="pending",
        description="BM Bossbot is reviewing this head SHA",
        target_url="https://github.com/basicmachines-co/basic-memory/actions/runs/1",
    )

    assert payload == {
        "state": "pending",
        "context": "BM Bossbot Approval",
        "description": "BM Bossbot is reviewing this head SHA",
        "target_url": "https://github.com/basicmachines-co/basic-memory/actions/runs/1",
    }


def test_upsert_summary_block_replaces_existing_block() -> None:
    body = "\n".join(
        [
            "Intro",
            "<!-- BM_BOSSBOT_SUMMARY:start -->",
            "Old summary",
            "<!-- BM_BOSSBOT_SUMMARY:end -->",
            "Footer",
        ]
    )

    updated = bm_bossbot_status.upsert_summary_block(body, "New summary")

    assert "Old summary" not in updated
    assert "New summary" in updated
    assert updated.startswith("Intro")
    assert updated.endswith("Footer")
