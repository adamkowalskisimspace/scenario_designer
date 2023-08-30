import json
from pathlib import Path
from litestar import get
from litestar.response import Template


@get("/scenarios/{scenario_name:str}/procedures/{procedure_index:int}")
async def get_handler(scenario_name: str, procedure_index: int) -> Template:
    path = Path(".") / "scenarios" / f"{scenario_name}.json"
    with open(path) as fp:
        scenario = json.load(fp)
    return Template(
        "scenarios/scenario_name/procedures/procedure_index/index.html",
        context={
            **scenario["meta_data"],
            "index": procedure_index,
            "procedure": scenario["procedures"][procedure_index],
        },
    )
