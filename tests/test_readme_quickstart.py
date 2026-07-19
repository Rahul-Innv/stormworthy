"""Keep the public README quickstart executable against the shipped API."""

from pathlib import Path


def _quickstart_block() -> str:
    readme = (Path(__file__).parents[1] / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Quickstart (offline, no API key)", 1)[1]
    return section.split("```python", 1)[1].split("```", 1)[0]


def test_readme_quickstart_prints_both_filled_lenses(capsys):
    exec(_quickstart_block(), {})

    lines = {" ".join(line.split()) for line in capsys.readouterr().out.splitlines()}
    assert "subject filled 1.0" in lines
    assert "technology filled 1.0" in lines
