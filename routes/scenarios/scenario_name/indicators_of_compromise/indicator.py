import json
from pathlib import Path
from litestar import get
from litestar.response import Template


@get("/scenarios/{scenario_name:str}/indicators_of_compromise/{indicator:str}")
async def get_handler(scenario_name: str, indicator: str) -> Template:
    path = Path(".") / "scenarios" / f"{scenario_name}.json"
    with open(path) as fp:
        scenario = json.load(fp)
    return Template(
        f"scenarios/scenario_name/indicators_of_compromise/indicator.html",
        context={
            **scenario["meta_data"],
            "indicator": indicator,
            "data": scenario["iocs"][indicator],
        },
    )
