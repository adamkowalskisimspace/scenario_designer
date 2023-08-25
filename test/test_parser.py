import pathlib
import json

import parse


def test_parse_scenarios():
    input_path = (
        pathlib.Path.home() / "code" / "chimera" / "Chimera-Content" / "scenarios"
    )
    output_path = pathlib.Path(".") / "scenarios"
    if output_path.exists():
        for file in output_path.iterdir():
            file.unlink()
        output_path.rmdir()
    output_path.mkdir()
    scenarios = parse.scenarios(input_path)
    for name, scenario in scenarios.items():
        with open(output_path / f"{name}.json", "w") as f:
            json.dump(scenario, f, indent=4)
