import pytest
from pydantic import ValidationError

from config.env import AppSettings


def settings(**values) -> AppSettings:
    return AppSettings(_env_file=None, **values)


def test_development_defaults_need_no_env() -> None:
    env = settings()
    assert env.app_env == "development"
    assert env.allowed_hosts_list == ["localhost", "127.0.0.1"]


def test_csv_lists_are_trimmed() -> None:
    env = settings(cors_allowed_origins=" https://a.test , ,https://b.test")
    assert env.cors_allowed_origins_list == ["https://a.test", "https://b.test"]


@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        ({}, "SECRET_KEY"),
        ({"secret_key": "s" * 40, "debug": True}, "DEBUG"),
        ({"secret_key": "s" * 40, "allowed_hosts": "*"}, "ALLOWED_HOSTS"),
    ],
)
def test_production_refuses_unsafe_values(overrides, problem: str) -> None:
    with pytest.raises(ValidationError, match=problem):
        settings(app_env="production", **overrides)


def test_production_accepts_safe_values() -> None:
    env = settings(app_env="production", secret_key="s" * 40, allowed_hosts="routeiq.example")
    assert env.is_production
