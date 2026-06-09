from pathlib import Path

import yaml


WORKFLOW_PATH = Path(".github/workflows/bm-bossbot.yml")
PROMPT_PATH = Path(".github/basic-memory/bm-bossbot-review.md")


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_bm_bossbot_uses_safe_pull_request_target_gate() -> None:
    workflow = _workflow()

    assert workflow["name"] == "BM Bossbot"
    assert "pull_request_target" in workflow["on"]
    assert workflow["on"]["pull_request_target"]["types"] == [
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
    ]
    assert "workflow_dispatch" in workflow["on"]

    permissions = workflow["permissions"]
    assert permissions["contents"] == "read"
    assert permissions["pull-requests"] == "write"
    assert permissions["statuses"] == "write"


def test_bm_bossbot_workflow_never_checks_out_untrusted_head() -> None:
    workflow = _workflow()
    review_job = workflow["jobs"]["review"]
    steps = review_job["steps"]
    checkout_step = next(step for step in steps if step.get("uses") == "actions/checkout@v6")

    assert checkout_step["with"]["ref"] == "${{ github.event.pull_request.base.ref || github.ref }}"
    assert "${{ github.event.pull_request.head.sha }}" not in str(checkout_step)
    assert "cancel-in-progress: true" in WORKFLOW_PATH.read_text(encoding="utf-8")


def test_bm_bossbot_workflow_has_deterministic_status_steps() -> None:
    workflow = _workflow()
    steps = workflow["jobs"]["review"]["steps"]
    names = [step["name"] for step in steps]

    assert "Set up uv" in names
    assert "Mark BM Bossbot approval pending" in names
    assert "Run BM Bossbot review with Codex" in names
    assert "Finalize BM Bossbot approval" in names

    run_codex = next(step for step in steps if step["name"] == "Run BM Bossbot review with Codex")
    assert run_codex["uses"] == "openai/codex-action@v1"
    assert run_codex["with"]["openai-api-key"] == "${{ secrets.OPENAI_API_KEY }}"
    assert "--output-schema" in run_codex["with"]["codex-args"]

    finalize = next(step for step in steps if step["name"] == "Finalize BM Bossbot approval")
    assert finalize["if"] == "always()"
    assert "BM Bossbot Approval" in WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "uv run --script scripts/bm_bossbot_status.py pending" in WORKFLOW_PATH.read_text(
        encoding="utf-8"
    )
    assert "uv run --script scripts/bm_bossbot_status.py finalize" in WORKFLOW_PATH.read_text(
        encoding="utf-8"
    )
    assert "uv run --script scripts/generate_pr_infographic.py" in WORKFLOW_PATH.read_text(
        encoding="utf-8"
    )
    assert "--provenance-output" in WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "BM_INFOGRAPHIC_PROVENANCE:start" in WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "BM_INFOGRAPHIC_PROVENANCE:end" in WORKFLOW_PATH.read_text(encoding="utf-8")


def test_bm_bossbot_prompt_references_engineering_style_and_json_bullets() -> None:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    assert "docs/ENGINEERING_STYLE.md" in prompt
    assert "- Set `reviewed_head_sha`" in prompt
    assert "- Do not include Markdown outside the JSON." in prompt


def test_claude_code_review_is_manual_advisory_only() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/claude-code-review.yml").read_text(encoding="utf-8")
    )

    assert "pull_request" not in workflow["on"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["on"]["workflow_dispatch"]["inputs"]["pr_number"]["required"] is True
