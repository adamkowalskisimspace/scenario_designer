import pathlib
import ast
from typing import Literal, TypedDict, Optional, cast
from random import randint, choice
import string


class Name(TypedDict):
    kind: Literal["name"]
    id: str


class Attribute(TypedDict):
    kind: Literal["attribute"]
    attr: "Value"
    value: "Value"


class Template(TypedDict):
    template: list["Value"]


class Slice(TypedDict):
    kind: Literal["slice"]
    slice: "Value"
    value: "Value"


Op = Literal["add"]


class BinOp(TypedDict):
    kind: Literal["bin op"]
    op: Op
    left: "Value"
    right: "Value"


class Call(TypedDict):
    kind: Literal["call"]
    func: "Value"
    args: list["Value"]


class Generator(TypedDict):
    iter: "Value"
    target: "Value"


class Comprehension(TypedDict):
    kind: Literal["comprehension"]
    element: "Value"
    generators: list[Generator]


Value = (
    Name
    | Attribute
    | Template
    | str
    | bool
    | int
    | list["Value"]
    | dict[str, "Value"]
    | Slice
    | BinOp
    | Call
    | Comprehension
)


class Procedure(TypedDict, total=False):
    tactic: str
    technique: str
    label: str
    preconditions: Value
    tune: Value


class MetaData(TypedDict):
    name: str
    version: str
    title: str
    description: str
    author: str
    suggested_duration: int


class Preconditions(TypedDict):
    state: dict[str, str]
    initial: Value
    effects: Value


class Scenario(TypedDict):
    meta_data: MetaData
    procedures: list[Procedure]
    iocs: Value
    spec: Value
    preconditions: Preconditions


Scenarios = dict[str, Scenario]


def bin_op(op: ast.operator) -> Op:
    match op:
        case ast.Add():
            return "add"
        case _:
            breakpoint()
            raise NotImplemented


def transform_value(expr: ast.expr) -> Value:
    match expr:
        case ast.Constant(value):
            match value:
                case str(s):
                    return s.strip()
                case bool() | int():
                    return value
                case _:
                    breakpoint()
                    raise NotImplemented
        case ast.Attribute(value, attr):
            assert isinstance(attr, str)
            transformed = transform_value(value)
            if isinstance(transformed, dict):
                if kind := transformed.get("kind"):
                    if kind == "name":
                        if id := transformed.get("id"):
                            if id == "self":
                                return f"self.{attr}"
            return {
                "kind": "attribute",
                "attr": attr,
                "value": transformed,
            }
        case ast.Dict(keys, values):
            keys = [transform_value(key) for key in keys if key is not None]
            values = [transform_value(value) for value in values]
            result: dict[str, Value] = {}
            for key, value in zip(keys, values):
                assert isinstance(key, str)
                result[key] = value
            return result
        case ast.JoinedStr(values):
            template = [transform_value(value) for value in values]
            match template:
                case []:
                    return ""
                case [str(s)]:
                    return s
                case _:
                    return {"template": template}
        case ast.FormattedValue(value):
            return transform_value(value)
        case ast.Subscript(value, slice):
            return {
                "kind": "slice",
                "slice": transform_value(slice),
                "value": transform_value(value),
            }
        case ast.BinOp(left, op, right):
            return {
                "kind": "bin op",
                "op": bin_op(op),
                "left": transform_value(left),
                "right": transform_value(right),
            }
        case ast.Tuple(elts):
            return [transform_value(elt) for elt in elts]
        case ast.List(elts):
            return [transform_value(elt) for elt in elts]
        case ast.Call(func, args, keywords):
            assert len(keywords) == 0
            return {
                "kind": "call",
                "func": transform_value(func),
                "args": [transform_value(arg) for arg in args],
            }
        case str(s):
            return s
        case ast.Name(id):
            return {"kind": "name", "id": id}
        case ast.GeneratorExp(elt, generators) | ast.ListComp(elt, generators):
            element = transform_value(elt)
            gens: list[Generator] = []
            for generator in generators:
                iter = transform_value(generator.iter)
                target = transform_value(generator.target)
                gens.append({"iter": iter, "target": target})
            return {
                "kind": "comprehension",
                "element": element,
                "generators": gens,
            }
        case _:
            breakpoint()
            raise NotImplemented


def preconditions(call: ast.Call) -> dict[str, Value]:
    assert len(call.keywords) == 1
    arg = call.keywords[0]
    assert arg.arg == "precondition"
    assert isinstance(arg.value, ast.Dict)
    precondition_map: dict[str, Value] = {}
    for key, value in zip(arg.value.keys, arg.value.values):
        assert key is not None
        transformed_key = transform_value(key)
        assert isinstance(transformed_key, str)
        transformed_value = transform_value(value)
        precondition_map[transformed_key] = transformed_value
    return precondition_map


def simplify(c: Value, context: dict[str, Value]) -> Value:
    match c:
        case {"template": list(t)}:
            final = ""
            for i, piece in enumerate(t):
                needs_interpolation = i % 2 == 1
                simplified = simplify(piece, context)
                match simplified:
                    case str(s) if s.startswith("self.") and needs_interpolation:
                        final += f"${{{s}}}"
                    case str() | int() | float() | bool():
                        final += str(simplified)
                    case _ if needs_interpolation:
                        final += f"${{{simplified}}}"
                    case _:
                        breakpoint()
                        raise NotImplemented
            return final
        case {
            "kind": "attribute",
            "attr": "ascii_uppercase",
            "value": {"kind": "name", "id": "string"},
        }:
            return string.ascii_uppercase
        case {
            "kind": "attribute",
            "attr": "digits",
            "value": {"kind": "name", "id": "string"},
        }:
            return string.digits
        case {"kind": "call", "func": f, "args": list(args)}:
            match f:
                case {"kind": "name", "id": "range"}:
                    assert len(args) == 1
                    stop = args[0]
                    assert isinstance(stop, int)
                    return randint(0, stop)
                case {"kind": "name", "id": "str"}:
                    assert len(args) == 1
                    return str(simplify(args[0], context))
                case {"kind": "name", "id": "time"}:
                    assert len(args) == 0
                    return randint(0, 100)
                case {"kind": "name", "id": "randint"}:
                    assert len(args) == 2
                    start, stop = args
                    assert isinstance(start, int) and isinstance(stop, int)
                    return randint(start, stop)
                case {"kind": "attribute", "attr": "join", "value": ""}:
                    simplified = simplify(args, context)
                    assert isinstance(simplified, list)
                    for arg in simplified:
                        assert isinstance(arg, str)
                    return "".join(cast(list[str], simplified))
                case {"kind": "name", "id": "choice"}:
                    simplified = simplify(args, context)
                    assert isinstance(simplified, list)
                    for arg in simplified:
                        assert isinstance(arg, str)
                    return choice(cast(list[str], simplified))
                case _:
                    return c
        case {"kind": "comprehension", "element": e, "generators": list(gs)}:
            additional_variables = {}
            for g in gs:
                match g:
                    case {"iter": i, "target": {"kind": "name", "id": str(name)}}:
                        additional_variables[name] = simplify(i, context)
                    case _:
                        breakpoint()
                        raise NotImplementedError
            return simplify(e, {**context, **additional_variables})
        case {"kind": "bin op", "op": "add", "left": left, "right": right}:
            match (simplify(left, context), simplify(right, context)):
                case (str(l), str(r)):
                    return l + r
                case _:
                    breakpoint()
                    raise NotImplementedError
        case {"kind": "name", "id": str(id)}:
            if entry := context.get(id, None):
                return entry
            breakpoint()
            raise NotImplementedError
        case dict(d):
            result: Value = {}
            for key, value in d.items():
                assert isinstance(key, str)
                result[key] = simplify(value, context)
            return result
        case list(l):
            return [simplify(e, context) for e in l]
        case str() | bool() | int():
            return c
        case _:
            breakpoint()
            raise NotImplemented


def procedure_add(call: ast.Call) -> Procedure:
    assert len(call.args) == 2
    arg0, arg1 = call.args
    assert isinstance(arg0, ast.Constant)
    assert isinstance(arg0.value, str)
    assert isinstance(arg1, ast.Call)
    func = arg1.func
    assert isinstance(func, ast.Attribute)
    technique = func.attr
    value = func.value
    assert isinstance(value, ast.Name)
    tactic = value.id
    precondition_map = preconditions(arg1)
    procedure: Procedure = {
        "tactic": tactic,
        "technique": technique,
        "label": arg0.value,
        "preconditions": precondition_map,
    }
    if tune := precondition_map.pop("tune", None):
        procedure["tune"] = simplify(tune, {})
    return procedure


def get_plan(function_def: ast.FunctionDef) -> list[Procedure]:
    procedures: list[Procedure] = []
    for body in function_def.body:
        if not isinstance(body, ast.Expr):
            continue
        value = body.value
        if not isinstance(value, ast.Call):
            continue
        func = value.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr == "procedure_add":
            procedures.append(procedure_add(value))
    return procedures


def constructor(name: str, function_def: ast.FunctionDef) -> MetaData:
    meta_data = {}
    for body in function_def.body:
        if not isinstance(body, ast.Assign):
            continue
        assert len(body.targets) == 1
        target = body.targets[0]
        assert isinstance(target, ast.Attribute)
        attr = target.attr
        if attr == "spec":
            continue
        value = body.value
        assert isinstance(value, ast.Constant)
        meta_data[attr] = transform_value(value)
    return {
        "name": name,
        "version": meta_data["version"],
        "title": meta_data["title"],
        "description": meta_data["description"],
        "author": meta_data["author"],
        "suggested_duration": meta_data["suggested_duration"],
    }


def actor_iocs(function_def: ast.FunctionDef) -> Value:
    iocs: dict[str, Value] = {}
    for body in function_def.body:
        match body:
            case ast.Assign(targets, value, type_comment):
                assert len(targets) == 1
                name = targets[0]
                assert isinstance(name, ast.Name)
                id = name.id
                assert type_comment is None
                transformed = transform_value(value)
                iocs[id] = transformed
            case ast.Return(value):
                result: dict[str, Value] = {}
                assert isinstance(value, ast.Dict)
                for key, value in zip(value.keys, value.values):
                    assert key is not None
                    transformed_key = transform_value(key)
                    transformed_value = transform_value(value)
                    assert isinstance(transformed_key, str)
                    assert isinstance(transformed_value, dict)
                    assert "kind" in transformed_value
                    assert transformed_value["kind"] == "name"
                    assert "id" in transformed_value
                    id = transformed_value["id"]
                    assert isinstance(id, str)
                    result[transformed_key] = iocs[id]
                return simplify(result, iocs)
    raise Exception("No return statement")


def trim_spec(exprs: list[ast.stmt], context: dict[str, Value]) -> list[ast.stmt]:
    match exprs[0]:
        case ast.Expr():
            return trim_spec(exprs[1:], context)
        case ast.Assign(targets, value):
            assert len(targets) == 1
            target = targets[0]
            match target:
                case ast.Name(id):
                    match id:
                        case "scenario_name":
                            assert isinstance(value, ast.Constant)
                            assert isinstance(value.value, str)
                            context["scenario_name"] = value.value
                            return trim_spec(exprs[1:], context)
                        case "spec":
                            assert isinstance(value, ast.Call)
                            func = value.func
                            assert isinstance(func, ast.Name)
                            assert func.id == "dict"
                            assert len(value.args) == 0
                            assert len(value.keywords) == 0
                            return trim_spec(exprs[1:], context)
                        case _:
                            return exprs
                case _:
                    return exprs
        case _:
            return exprs


def spec_default(function_def: ast.FunctionDef) -> Value:
    match function_def.body:
        case [return_]:
            assert isinstance(return_, ast.Return)
            assert return_.value is not None
            return simplify(transform_value(return_.value), {})
        case [assign, return_]:
            assert isinstance(assign, ast.Assign)
            assert len(assign.targets) == 1
            name = assign.targets[0]
            assert isinstance(name, ast.Name)
            assert name.id == "scenario_name"
            constant = assign.value
            assert isinstance(constant, ast.Constant)
            assert isinstance(constant.value, str)
            assert isinstance(return_, ast.Return)
            assert return_.value is not None
            context: dict[str, Value] = {"scenario_name": constant.value}
            return simplify(transform_value(return_.value), context)
        case exprs:
            context = {}
            *assigns, return_ = trim_spec(exprs, context)
            spec: dict[str, Value] = {}
            for assign in assigns:
                assert isinstance(assign, ast.Assign)
                assert len(assign.targets) == 1
                target = assign.targets[0]
                assert isinstance(target, ast.Subscript)
                name = target.value
                assert isinstance(name, ast.Name)
                assert name.id == "spec"
                key = target.slice
                assert isinstance(key, ast.Constant)
                assert isinstance(key.value, str)
                value = transform_value(assign.value)
                spec[key.value] = value
            return simplify(spec, context)


Arguments = tuple[ast.Attribute, ast.List | ast.Constant, Optional[ast.Constant]]
Keywords = list[ast.keyword]


def preconditions_arguments(args: list[ast.expr], keywords: Keywords) -> Arguments:
    match args, keywords:
        case [], [preconditions, value_path]:
            assert preconditions.arg == "preconditions"
            assert value_path.arg == "value_path"
            assert isinstance(preconditions.value, ast.Attribute)
            assert isinstance(value_path.value, ast.List)
            return preconditions.value, value_path.value, None
        case [], [preconditions, value_path, default]:
            assert preconditions.arg == "preconditions"
            assert value_path.arg == "value_path"
            assert default.arg == "default"
            assert isinstance(preconditions.value, ast.Attribute)
            assert isinstance(value_path.value, ast.List)
            assert isinstance(default.value, ast.Constant)
            return preconditions.value, value_path.value, default.value
        case [preconditions, value_path], []:
            assert isinstance(preconditions, ast.Attribute)
            L, C = ast.List, ast.Constant
            assert isinstance(value_path, L) or isinstance(value_path, C)
            return preconditions, value_path, None
        case [preconditions], [value_path]:
            assert isinstance(preconditions, ast.Attribute)
            assert value_path.arg == "value_path"
            assert isinstance(value_path.value, ast.List)
            return preconditions, value_path.value, None
        case _:
            breakpoint()
            raise NotImplemented


def set_precondition(function_def: ast.FunctionDef) -> Preconditions:
    state: dict[str, str] = {}
    initial: dict[str, Value] = {}
    effects: dict[str, Value] = {}
    for expr in function_def.body:
        match expr:
            case ast.Assign(targets, value):
                assert len(targets) == 1
                target = targets[0]
                assert isinstance(target, ast.Attribute)
                key = target.attr
                if key == "ioc_spec":
                    continue
                assert isinstance(key, str)
                name = target.value
                assert isinstance(name, ast.Name)
                assert name.id == "self"
                match value:
                    case ast.Call(func, args, keywords):
                        assert isinstance(func, ast.Attribute)
                        assert func.attr == "test_precondition"
                        arguments = preconditions_arguments(args, keywords)
                        preconditions, value_path, default = arguments
                        transformed_path = transform_value(value_path)
                        transformed_default = None
                        if default is not None:
                            transformed_default = transform_value(default)
                        obj = {"path": transformed_path}
                        if transformed_default is not None:
                            obj["default"] = transformed_default
                        match preconditions.attr:
                            case "ioc_spec":
                                initial[key] = obj
                            case "preconditions":
                                effects[key] = obj
                            case _:
                                breakpoint()
                                raise NotImplemented
                    case ast.Constant(value):
                        assert isinstance(value, str)
                        state[key] = value
                    case _:
                        breakpoint()
                        raise NotImplemented
            case ast.Expr(value):
                match value:
                    case ast.Call(func, args, keywords):
                        assert len(args) == 0
                        assert len(keywords) == 0
                        assert isinstance(func, ast.Attribute)
                        assert func.attr == "procedures_reset"
                        name = func.value
                        assert isinstance(name, ast.Name)
                        assert name.id == "self"
                    case ast.Constant(value):
                        assert isinstance(value, str)
                    case _:
                        breakpoint()
                        raise NotImplemented
            case _:
                breakpoint()
                raise NotImplemented
    return {"state": state, "initial": initial, "effects": effects}


def file_name_no_suffix(path: pathlib.Path) -> str:
    return path.name[: -len(path.suffix)]


def scenario(file: pathlib.Path) -> Optional[Scenario]:
    name = file_name_no_suffix(file)
    if name == "__init__":
        return
    module = ast.parse(file.read_text())
    procedures: list[Procedure] = []
    meta_data: Optional[MetaData] = None
    iocs: Optional[Value] = None
    spec: Optional[Value] = None
    preconditions: Optional[Preconditions] = None
    for top_level in module.body:
        if not isinstance(top_level, ast.ClassDef):
            continue
        for member in top_level.body:
            if not isinstance(member, ast.FunctionDef):
                continue
            match member.name:
                case "get_plan":
                    procedures = get_plan(member)
                case "__init__":
                    meta_data = constructor(name, member)
                case "actor_iocs":
                    iocs = actor_iocs(member)
                case "spec_default":
                    spec = spec_default(member)
                case "set_precondition":
                    preconditions = set_precondition(member)
    assert len(procedures) > 0
    assert meta_data is not None
    assert iocs is not None
    assert spec is not None
    assert preconditions is not None
    return {
        "meta_data": meta_data,
        "procedures": procedures,
        "iocs": iocs,
        "spec": spec,
        "preconditions": preconditions,
    }


def scenarios(path: pathlib.Path) -> Scenarios:
    scenario_map = {}
    for file in path.iterdir():
        if s := scenario(file):
            scenario_map[s["meta_data"]["name"]] = s
    return scenario_map
