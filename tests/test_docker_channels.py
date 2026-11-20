import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from docker_channels import docker_tags


@pytest.mark.parametrize(
    ("ref", "version", "expected"),
    [
        ("refs/heads/main", "0.2.0b26", "type=raw,value=edge"),
        ("refs/heads/main", "0.2.0", "type=raw,value=edge"),
        ("refs/tags/v0.2.0b26", "0.2.0b26", "type=raw,value=v0.2.0b26\ntype=raw,value=beta"),
        ("refs/tags/v0.2.0", "0.2.0", "type=raw,value=v0.2.0\ntype=raw,value=latest"),
    ],
)
def test_docker_tags(ref, version, expected):
    assert docker_tags(ref, version) == expected


@pytest.mark.parametrize(
    ("ref", "version"),
    [
        ("refs/heads/feature", "0.2.0"),
        ("refs/tags/v0.2.0b25", "0.2.0b26"),
        ("refs/tags/v0.2.0-rc.1", "0.2.0-rc.1"),
        ("refs/tags/vlatest", "latest"),
    ],
)
def test_invalid_docker_tags(ref, version):
    with pytest.raises(ValueError):
        docker_tags(ref, version)
