from __future__ import annotations

import pytest

from llm_feature_workflow.config import WorkflowError
from llm_feature_workflow.profiles import load_profiles, resolve_profiles, validate_kind
from llm_feature_workflow.specs import parse_module, parse_service, parse_setting, parse_uses


def test_parse_declarative_specs() -> None:
    module = parse_module("api:backend=python+fastapi")
    assert module.name == "api"
    assert module.kind == "backend"
    assert module.profiles == ["python", "fastapi"]
    assert parse_service("database=postgres") == ("database", "postgres")
    assert parse_uses("api=database,cache") == ("api", ["database", "cache"])
    assert parse_setting("api.package_manager=uv") == ("api", "package_manager", "uv")


def test_invalid_module_has_helpful_error() -> None:
    with pytest.raises(WorkflowError, match="nome:tipo=perfil"):
        parse_module("python+fastapi")


def test_profile_dependencies_and_conflicts() -> None:
    registry = load_profiles()
    assert resolve_profiles(["fastapi"], registry) == ["python", "fastapi"]
    assert resolve_profiles(["compose"], registry) == ["kotlin", "android", "compose"]
    with pytest.raises(WorkflowError, match="conflita"):
        resolve_profiles(["fastapi", "django"], registry)


def test_profile_kind_is_validated() -> None:
    registry = load_profiles()
    with pytest.raises(WorkflowError, match="não se aplica"):
        validate_kind("mobile", resolve_profiles(["fastapi"], registry), registry)
