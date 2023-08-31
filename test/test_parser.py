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
