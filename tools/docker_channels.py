"""Map an Ocean2MQTT release ref to its allowed Docker tags."""

import os
import re
import tomllib
from pathlib import Path

_RELEASE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(b[0-9]+)?")


def docker_tags(ref: str, version: str) -> str:
    if ref == "refs/heads/main":
        return "type=raw,value=edge"

    prefix = "refs/tags/v"
    if not ref.startswith(prefix):
        raise ValueError("La publication requiert main ou un tag de version v…")

    tagged_version = ref.removeprefix(prefix)
    match = _RELEASE.fullmatch(tagged_version)
    if match is None or tagged_version != version:
        raise ValueError(f"Tag {ref} incompatible avec la version {version} de pyproject.toml")

    channel = "beta" if match.group(4) else "latest"
    return f"type=raw,value=v{version}\ntype=raw,value={channel}"


if __name__ == "__main__":
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    print("tags<<TAGS")
    print(docker_tags(os.environ["GITHUB_REF"], version))
    print("TAGS")
