"""Generate observed dependency versions/licenses without assigning Agent a license."""
from importlib.metadata import distributions
import json
import re
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    # A global Windows Python installation can contain packages for other projects.
    # Inventory only distributions declared in this project's locked profiles.
    declared = set()
    for lock in root.glob("requirements*.txt"):
        for line in lock.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)[=<>\[]", line)
            if match:
                declared.add(re.sub(r"[-_.]+", "-", match[1]).lower())
    python = []
    for distribution in distributions():
        metadata = distribution.metadata
        if re.sub(r"[-_.]+", "-", metadata["Name"]).lower() not in declared:
            continue
        license_value = metadata.get("License-Expression") or metadata.get("License") or "unspecified"
        if len(license_value) > 200:
            license_value = "see distribution license files"
        python.append({"name": metadata["Name"], "version": distribution.version,
                       "license_metadata": license_value})
    javascript = {}
    for path in (root / "web" / "node_modules" / ".pnpm").glob("*/node_modules/**/package.json"):
        if "node_modules" not in path.parts:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if value.get("name") and value.get("version"):
            key = value["name"] + "@" + value["version"]
            javascript[key] = {"name": value["name"], "version": value["version"],
                               "license_metadata": value.get("license", "unspecified")}
    result = {"scope": "Installed distributions declared by the project's locked profiles",
              "agent_license": "not declared; owner decision required",
              "python": sorted(python, key=lambda x: x["name"].casefold()),
              "javascript": sorted(javascript.values(), key=lambda x: (x["name"], x["version"])),
              "note": "Package metadata inventory; consult supplied license texts before redistribution"}
    target = root / "docs" / "dependencies.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(python)} Python distributions, {len(javascript)} JavaScript package versions")


if __name__ == "__main__":
    main()
