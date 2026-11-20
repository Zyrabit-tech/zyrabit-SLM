import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "check_compose_docker_sock.py"
spec = importlib.util.spec_from_file_location("check_compose_docker_sock", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_default_compose_uses_socket_proxy_and_hides_chroma():
    text = (ROOT / "zyrabit-slm" / "docker-compose.yml").read_text(encoding="utf-8")
    module.assert_api_does_not_mount_raw_docker_sock(text)
    module.assert_chroma_not_published(text)


def test_raw_docker_sock_on_api_is_rejected():
    bad = """
services:
  zyrabit-docker-proxy:
    image: tecnativa/docker-socket-proxy:0.3.0
    environment:
      CONTAINERS: 1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
  zyrabit-api:
    environment:
      - DOCKER_HOST=tcp://zyrabit-docker-proxy:2375
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
  zyrabit-db:
    expose:
      - "8000"
"""
    with pytest.raises(module.ComposeDockerSockError):
        module.assert_api_does_not_mount_raw_docker_sock(bad)


def test_published_chroma_port_is_rejected():
    bad = """
services:
  zyrabit-db:
    ports:
      - "127.0.0.1:8000:8000"
"""
    with pytest.raises(module.ComposeDockerSockError):
        module.assert_chroma_not_published(bad)
