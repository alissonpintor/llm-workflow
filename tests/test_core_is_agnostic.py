from __future__ import annotations

from importlib.resources import files


def test_core_does_not_embed_stack_or_domain_names() -> None:
    core = files("llm_feature_workflow").joinpath("assets", "core")
    forbidden = (
        "fastapi",
        "django",
        "kotlin",
        "ktor",
        "svelte",
        "sankhya",
        "gradle",
        "postgres",
        "redis",
        "playwright",
    )
    violations: list[str] = []
    for group in core.iterdir():
        if not group.is_dir():
            continue
        for path in group.iterdir():
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8").lower()
            matched = [word for word in forbidden if word in text]
            if matched:
                violations.append(f"{group.name}/{path.name}: {', '.join(matched)}")
    assert not violations, violations
