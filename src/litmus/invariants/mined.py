from __future__ import annotations

import ast
from pathlib import Path

from litmus.invariants.models import (
    Invariant,
    InvariantStatus,
    InvariantType,
    RequestExample,
    ResponseExample,
)


def mine_invariants_from_tests(paths: list[Path | str]) -> list[Invariant]:
    invariants: list[Invariant] = []

    for path in paths:
        invariants.extend(_mine_invariants_from_test_file(Path(path)))

    return invariants


def _mine_invariants_from_test_file(path: Path) -> list[Invariant]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mined: list[Invariant] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue

        request_payload = _extract_literal_assignment(node, "request")
        response_payload = _extract_literal_assignment(node, "response")
        status_code = _extract_response_status_code(node)

        if response_payload is None and status_code is not None:
            response_payload = {"status_code": status_code}
        elif response_payload is not None and status_code is not None:
            response_payload.setdefault("status_code", status_code)

        mined.append(
            Invariant(
                name=node.name.removeprefix("test_"),
                source=f"mined:{path.as_posix()}::{node.name}",
                status=InvariantStatus.CONFIRMED,
                type=InvariantType.DIFFERENTIAL,
                request=RequestExample.model_validate(request_payload) if request_payload else None,
                response=ResponseExample.model_validate(response_payload) if response_payload else None,
            )
        )

    return mined


def _extract_literal_assignment(node: ast.FunctionDef, variable_name: str) -> dict | None:
    for statement in node.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == variable_name for target in statement.targets):
            continue
        try:
            value = ast.literal_eval(statement.value)
        except (ValueError, SyntaxError):
            return None
        if isinstance(value, dict):
            return value
    return None


def _extract_response_status_code(node: ast.FunctionDef) -> int | None:
    for statement in node.body:
        if not isinstance(statement, ast.Assert):
            continue
        test = statement.test
        if not isinstance(test, ast.Compare):
            continue
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq) or len(test.comparators) != 1:
            continue
        comparator = test.comparators[0]
        if not isinstance(comparator, ast.Constant) or not isinstance(comparator.value, int):
            continue
        if _is_response_status_lookup(test.left):
            return comparator.value
    return None


def _is_response_status_lookup(node: ast.AST) -> bool:
    if not isinstance(node, ast.Subscript):
        return False
    if not isinstance(node.value, ast.Name) or node.value.id != "response":
        return False
    if isinstance(node.slice, ast.Constant):
        return node.slice.value == "status_code"
    return False
