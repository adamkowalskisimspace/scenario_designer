import json
from pathlib import Path
from litestar import get
from litestar.response import Template


@get("/scenarios/{scenario_name:str}")
async def get_handler(scenario_name: str) -> Template:
    path = Path(".") / "scenarios" / f"{scenario_name}.json"
    with open(path) as fp:
        scenario = json.load(fp)
    return Template(
        "scenarios/scenario_name/index.html",
        context=scenario["meta_data"],
    )
