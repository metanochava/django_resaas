"""
Common result type + a tiny check registry for `resaas_doctor`/
`resaas_check`/`resaas_schema_check`.

Mirrors the VIEW_REGISTRY/register_view pattern already used for views
(core/base/registry.py) on purpose - a plain module-level dict plus a
decorator that registers into it, so any app (notifications, hr, sales, ...)
can contribute a check just by importing this module and decorating a
`Check` subclass, without this file ever needing to know about them.
"""

from dataclasses import dataclass, field

LEVELS = ("info", "success", "warning", "error")


@dataclass
class CheckResult:
    code: str
    level: str
    message: str
    context: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "code": self.code,
            "level": self.level,
            "message": self.message,
            "context": self.context,
        }


# {check.name: check_instance}
CHECK_REGISTRY: dict[str, "Check"] = {}


def register_check(check_cls):
    """Class decorator - instantiates `check_cls` and registers it under
    its own `name`. Checks are stateless, so one shared instance per class
    is enough."""
    instance = check_cls()
    CHECK_REGISTRY[instance.name] = instance
    return check_cls


class Check:
    """Base class for a doctor check. Subclasses set `name` (used for
    --check filtering and as the JSON key) and `label` (human heading),
    and implement `run()`. A check must never write to the database -
    it observes and reports, nothing more (see resaas_doctor/resaas_check:
    they exist specifically to be safe to run in production/CI)."""

    name: str = None
    label: str = None

    def run(self) -> list[CheckResult]:
        raise NotImplementedError
