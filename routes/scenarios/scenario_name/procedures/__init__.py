import json
from pathlib import Path
from litestar import get
from litestar.response import Template


@get("/scenarios/{scenario_name:str}/procedures")
async def get_handler(scenario_name: str) -> Template:
    path = Path(".") / "scenarios" / f"{scenario_name}.json"
    with open(path) as fp:
        scenario = json.load(fp)
    procedures = []
    for procedure in scenario["procedures"]:
        preconditions = procedure["preconditions"]
        targets = []
        for name, value in preconditions.items():
            if name.startswith("target"):
                targets.append({"name": name, "value": value})
        procedure["targets"] = targets
        procedures.append(procedure)
    return Template(
        "scenarios/scenario_name/procedures/index.html",
        context={
            **scenario["meta_data"],
            "procedures": procedures,
        },
    )
