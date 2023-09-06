import pathlib
import json

from compiler import parse

input_path = pathlib.Path.home() / "code" / "chimera" / "Chimera-Content" / "scenarios"

output_path = pathlib.Path(".") / "scenarios"


def delete_existing_scenarios() -> None:
    if not output_path.exists():
        return
    for file in output_path.iterdir():
        file.unlink()
    output_path.rmdir()


def write_scenarios(scenarios: parse.Scenarios) -> None:
    for name, scenario in scenarios.items():
        with open(output_path / f"{name}.json", "w") as f:
            json.dump(scenario, f, indent=4)


def test_parse_scenarios():
    delete_existing_scenarios()
    output_path.mkdir()
    scenarios = parse.scenarios(input_path)
    write_scenarios(scenarios)


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
