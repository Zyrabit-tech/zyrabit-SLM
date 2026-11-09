"""Release refs must not let a beta tag move the stable image pointer."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "resolve_release_channel.py"
spec = importlib.util.spec_from_file_location("resolve_release_channel", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_docker_hub_wildcard_rule_freezes_moving_tags():
    settings = {"enabled": True, "rules": [".*"]}
    assert module.docker_hub_tag_is_immutable("beta", settings)
    assert module.docker_hub_tag_is_immutable("latest", settings)
    assert module.docker_hub_tag_is_immutable("2.4.8-beta.3", settings)
    assert not module.docker_hub_tag_is_immutable("beta", {"enabled": False, "rules": [".*"]})


def test_beta_tag_never_publishes_latest():
    plan = module.resolve_release_channel("v2.4.8-beta.1", "2.4.8", commit_on_main=False)
    assert plan["channel"] == "beta"
    assert plan["mutable_tags"] == "beta"
    assert plan["immutable_tags"] == "2.4.8-beta.1"
    assert "latest" not in plan["mutable_tags"]
    assert "latest" not in plan["immutable_tags"]


def test_plain_version_tag_off_main_is_rejected():
    with pytest.raises(module.ReleaseRefError):
        module.resolve_release_channel("v2.4.9", "2.4.9", commit_on_main=False)


def test_stable_tag_on_main_publishes_latest_when_version_matches():
    plan = module.resolve_release_channel("v2.4.8", "2.4.8", commit_on_main=True)
    assert plan["channel"] == "stable"
    assert plan["immutable_tags"] == "2.4.8"
    assert plan["mutable_tags"] == "latest"


def test_stable_tag_must_match_version_file():
    with pytest.raises(module.ReleaseRefError):
        module.resolve_release_channel("v2.4.9", "2.4.8", commit_on_main=True)


def test_branch_push_does_not_select_a_channel():
    plan = module.resolve_release_channel("beta", "2.4.8", commit_on_main=False)
    assert plan["channel"] == "skip"
    assert plan["mutable_tags"] == ""


def test_github_output_appends_to_existing_image_names(tmp_path: Path):
    output = tmp_path / "github-output.txt"
    output.write_text("image=zyrabitcore/zyrabit-slm\nghcr=ghcr.io/zyrabit-tech/zyrabit-slm\n", encoding="utf-8")
    plan = module.resolve_release_channel("v2.4.8-beta.1", "2.4.8", commit_on_main=False)
    module.write_github_output(plan, output)
    text = output.read_text(encoding="utf-8")
    assert "image=zyrabitcore/zyrabit-slm" in text
    assert "ghcr=ghcr.io/zyrabit-tech/zyrabit-slm" in text
    assert "channel=beta" in text


def test_beta_branch_does_not_mint_a_stable_tag():
    existing = {"v2.4.8", "v2.4.7"}
    assert module.next_beta_tag("2.4.8", existing) == "v2.4.8-beta.1"
    assert module.next_beta_tag("2.4.8", existing | {"v2.4.8-beta.1"}) is None
    assert "v2.4.8" != module.next_beta_tag("2.4.9", set())


def test_ledger_requires_both_architectures(tmp_path: Path):
    plan = module.resolve_release_channel("v2.4.8", "2.4.8", commit_on_main=True)
    with pytest.raises(module.ReleaseRefError):
        module.format_ledger(plan, "a" * 40, {"amd64": "sha256:abc"})

    text = module.format_ledger(
        plan,
        "a" * 40,
        {"amd64": "sha256:abc", "arm64": "sha256:def"},
    )
    assert '"sha": "' + ("a" * 40) + '"' in text
    assert "sha256:def" in text
