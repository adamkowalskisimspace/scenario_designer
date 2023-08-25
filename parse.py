import pathlib
import ast
from typing import Literal, TypedDict, Optional


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


class Procedure(TypedDict):
    tactic: str
    technique: str
    label: str
    preconditions: dict[str, Value]


class MetaData(TypedDict):
    name: str
    version: str
    title: str
    description: str
    author: str
    suggested_duration: int


class Scenario(TypedDict):
    meta_data: MetaData
    procedures: list[Procedure]
    iocs: dict[str, Value]


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
                case str() | bool() | int():
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
            return template[0] if len(template) == 1 else {"template": template}
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


def procedure_add(call: ast.Call) -> Procedure:
    assert len(call.args) == 2
    arg0, arg1 = call.args
    assert isinstance(arg0, ast.Constant)
    assert isinstance(arg0.value, str)
    assert isinstance(arg1, ast.Call)
    func = arg1.func
    assert isinstance(func, ast.Attribute)
    tactic = func.attr
    value = func.value
    assert isinstance(value, ast.Name)
    technique = value.id
    return {
        "tactic": tactic,
        "technique": technique,
        "label": arg0.value,
        "preconditions": preconditions(arg1),
    }


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
        meta_data[attr] = value.value
    return {
        "name": name,
        "version": meta_data["version"],
        "title": meta_data["title"],
        "description": meta_data["description"],
        "author": meta_data["author"],
        "suggested_duration": meta_data["suggested_duration"],
    }


def actor_iocs(function_def: ast.FunctionDef) -> dict[str, Value]:
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
                return result
    raise Exception("No return statement")


def file_name_no_suffix(path: pathlib.Path) -> str:
    return path.name[: -len(path.suffix)]


def scenario(file: pathlib.Path) -> Optional[Scenario]:
    name = file_name_no_suffix(file)
    if name == "__init__":
        return
    module = ast.parse(file.read_text())
    procedures: list[Procedure] = []
    meta_data: Optional[MetaData] = None
    iocs: Optional[dict[str, Value]] = None
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
    assert len(procedures) > 0
    assert meta_data is not None
    assert iocs is not None
    return {"meta_data": meta_data, "procedures": procedures, "iocs": iocs}


def scenarios(path: pathlib.Path) -> dict[str, Scenario]:
    scenario_map = {}
    for file in path.iterdir():
        if s := scenario(file):
            scenario_map[s["meta_data"]["name"]] = s
    return scenario_map
