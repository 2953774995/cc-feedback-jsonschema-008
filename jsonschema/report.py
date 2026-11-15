"""
Aggregated validation error reporting.

The core validator APIs either stop at the first error
(`jsonschema.validate`) or yield a flat stream of `ValidationError`
objects whose paths are relative to the subschema that produced them
(`jsonschema.protocols.Validator.iter_errors`). This module turns that
stream into a field-oriented report: every error is collected, located
by a complete `JSON Pointer <https://www.rfc-editor.org/rfc/rfc6901>`_,
and grouped by location for direct use in defect reports or dashboards.
"""

from dataclasses import dataclass
from typing import Any

from jsonschema.validators import validator_for

__all__ = ["ErrorItem", "Report", "summarize"]


def _escape(token: str) -> str:
    # RFC 6901: "~" must be escaped before "/".
    return token.replace("~", "~0").replace("/", "~1")


def _to_pointer(path) -> str:
    return "".join("/" + _escape(str(part)) for part in path)


@dataclass(frozen=True)
class ErrorItem:
    """
    A single validation failure located at ``pointer``.

    Attributes:

        pointer:
            JSON Pointer to the offending instance location, e.g.
            ``/age`` or ``/tags/0``. The empty string (``""``) points
            at the document root.

        validator:
            Name of the failing JSON Schema keyword, e.g. ``"type"`` or
            ``"minimum"``. May be ``None`` when no keyword is involved
            (for instance a ``False`` schema).

        message:
            Human-readable failure message taken from the underlying
            `jsonschema.exceptions.ValidationError`.
    """

    pointer: str
    validator: str | None
    message: str


@dataclass(frozen=True)
class Report:
    """
    The aggregated result of validating one instance.

    Attributes:

        ok:
            ``True`` exactly when :attr:`errors` is empty.

        errors:
            Every error produced by the validator, in iteration order.

        by_pointer:
            The same errors grouped by :attr:`ErrorItem.pointer`.
    """

    ok: bool
    errors: list[ErrorItem]
    by_pointer: dict[str, list[ErrorItem]]


def summarize(schema: Any, instance: Any) -> Report:
    """
    Validate ``instance`` under ``schema`` and aggregate all errors.

    Unlike `jsonschema.validate`, validation does not stop at the first
    failure: every error from the validator is collected. Each error is
    located by an absolute JSON Pointer built from the full error path
    (including paths inherited from parent errors), so callers never
    have to join relative paths themselves.

    Raises:

        jsonschema.exceptions.SchemaError:

            if ``schema`` is itself invalid. The error from the
            metaschema check is propagated rather than swallowed,
            matching `jsonschema.validate`.
    """
    cls = validator_for(schema)
    cls.check_schema(schema)

    items = [
        ErrorItem(
            pointer=_to_pointer(error.absolute_path),
            validator=error.validator,
            message=error.message,
        )
        for error in cls(schema).iter_errors(instance)
    ]

    by_pointer: dict[str, list[ErrorItem]] = {}
    for item in items:
        by_pointer.setdefault(item.pointer, []).append(item)

    return Report(ok=not items, errors=items, by_pointer=by_pointer)
