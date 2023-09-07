import pathlib
import json

from compiler import parse

input_path = pathlib.Path.home() / "code" / "chimera" / "Chimera-Content" / "scenarios"

output_path = pathlib.Path(".") / "scenarios"


def test_parse_scenarios():
    scenarios = parse.scenarios(input_path)


Precondition = str
Technique = str
Tactic = str
Catalog = dict[Tactic, dict[Technique, list[Precondition]]]


def test_catalog():
    scenarios = parse.scenarios(input_path)
    catalog: Catalog = {}
    for scenario in scenarios.values():
        for procedure in scenario["procedures"]:
            assert "tactic" in procedure
            tactic_name = procedure["tactic"]
            if tactic_name not in catalog:
                catalog[tactic_name] = {}
            tactic = catalog[tactic_name]
            assert "technique" in procedure
            technique_name = procedure["technique"]
            if technique_name not in tactic:
                tactic[technique_name] = []
            assert "preconditions" in procedure
            preconditions = procedure["preconditions"]
            assert isinstance(preconditions, dict)
            technique = tactic[technique_name]
            for name in preconditions.keys():
                if name not in technique:
                    technique.append(name)
    with open("catalog.json", "w") as f:
        json.dump(catalog, f, indent=4)


def transform_state(scenarios):
    for name, scenario in scenarios.items():
        preconditions = scenario["preconditions"]
        state = preconditions["state"]
        assert isinstance(state, dict)
        initial = preconditions["initial"]
        assert isinstance(initial, dict)
        for name, value in initial.items():
            assert isinstance(value, dict)
            assert len(value) == 1
            assert "path" in value
            path = value["path"]
            if isinstance(path, list):
                full_path = ["spec"]
                for p in path:
                    assert isinstance(p, str)
                    full_path.append(p)
                state[name] = ".".join(full_path)
            else:
                assert isinstance(path, str)
                state[name] = path
        effects = preconditions["effects"]
        assert isinstance(effects, dict)
        for name, value in effects.items():
            assert isinstance(value, dict)
            assert "path" in value
            [label, *path] = value["path"]
            procedures = [p for p in scenario["procedures"] if p["label"] == label]
            if len(procedures) != 1:
                assert len(procedures) == 0
                continue
            procedure = procedures[0]
            full_path = ["postconditions"]
            for p in path:
                assert isinstance(p, str)
                full_path.append(p)
            assert "set_state" not in procedure
            procedure["set_state"] = {name: ".".join(full_path)}
        del scenario["preconditions"]
        scenario["state"] = state
    return scenarios


def transform_targets(scenarios):
    for scenario in scenarios.values():
        for target in scenario["spec"]["targets"].values():
            match target:
                case {"query": {"tag": {"domain_controller": "true"}}}:
                    target["query"] = {
                        "#projection": [
                            "$hostname",
                            "$os_version",
                            "$in_game_ip",
                            "$control_ip",
                        ],
                        "$tag": {"domain_controller": "true"},
                    }
                case _:
                    target["query"] = {
                        "#projection": [
                            "$hostname",
                            "$os_version",
                            "$in_game_ip",
                            "$control_ip",
                            "$username",
                            "$password",
                            "$email",
                            "$domain_name",
                            "$domain_admin_name",
                            "$domain_admin_password",
                        ],
                        "$tier": "4",
                    }
    return scenarios


def test_end_to_end():
    if not output_path.exists():
        return
    for file in output_path.iterdir():
        file.unlink()
    output_path.rmdir()
    output_path.mkdir()
    scenarios = parse.scenarios(input_path)
    scenarios = transform_state(scenarios)
    scenarios = transform_targets(scenarios)
    for name, scenario in scenarios.items():
        with open(output_path / f"{name}.json", "w") as f:
            json.dump(scenario, f, indent=4)
