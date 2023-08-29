from typing import cast
from compiler.parse import Scenarios, Scenario, Procedure, Value


def template(t: Value):
    assert isinstance(t, list)
    for piece in t:
        if not isinstance(piece, str):
            return {"template": t}
    result = ""
    for i, piece in enumerate(t):
        result += piece if i % 2 == 0 else f"${{{piece}}}"
    return result


def command(c: Value) -> Value:
    match c:
        case str(s):
            return s
        case {"template": t}:
            return template(t)
        case _:
            raise ValueError(f"Invalid command: {c}")


def tune(t: Value) -> Value:
    assert isinstance(t, dict)
    result: dict[str, Value] = {}
    for key, value in t.items():
        value = cast(Value, value)
        if key == "command":
            result[key] = command(value)
        else:
            result[key] = value
    return result


Preconditions = dict[str, Value]


def preconditions(ps: Preconditions) -> Preconditions:
    return {key: tune(value) if key == "tune" else value for key, value in ps.items()}


def procedure(p: Procedure) -> Procedure:
    return {**p, "preconditions": preconditions(p["preconditions"])}


def procedures(ps: list[Procedure]) -> list[Procedure]:
    return [procedure(p) for p in ps]


def scenario(s: Scenario) -> Scenario:
    return {**s, "procedures": procedures(s["procedures"])}


def scenarios(ss: Scenarios) -> Scenarios:
    return {name: scenario(s) for name, s in ss.items()}
