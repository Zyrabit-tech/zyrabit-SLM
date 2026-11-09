import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "check_traefik_dashboard.py"
spec = importlib.util.spec_from_file_location("check_traefik_dashboard", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_default_compose_does_not_publish_the_dashboard():
    text = (ROOT / "zyrabit-slm" / "docker-compose.yml").read_text(encoding="utf-8")
    module.assert_default_dashboard_closed(text)


def test_optional_dashboard_without_auth_is_rejected():
    with pytest.raises(module.DashboardConfigError):
        module.assert_optional_dashboard(True, "")
    with pytest.raises(module.DashboardConfigError):
        module.assert_optional_dashboard(True, "admin")


def test_optional_dashboard_with_basic_auth_is_accepted():
    module.assert_optional_dashboard(False, "")
    module.assert_optional_dashboard(True, "admin:$2y$05$examplehash")
