import json
from pathlib import Path
from litestar import get
from litestar.response import Template


@get("/scenarios/{scenario_name:str}/procedures/{procedure_index:int}")
async def get_handler(scenario_name: str, procedure_index: int) -> Template:
    path = Path(".") / "scenarios" / f"{scenario_name}.json"
    with open(path) as fp:
        scenario = json.load(fp)
    procedure = scenario["procedures"][procedure_index]
    with open(Path(".") / "catalog.json") as fp:
        catalog = json.load(fp)
    selected_tactic = procedure["tactic"]
    tactics = sorted(tactic for tactic in catalog.keys() if tactic != selected_tactic)
    selected_technique = procedure["technique"]
    techniques = sorted(
        technique
        for technique in catalog[selected_tactic].keys()
        if technique != selected_technique
    )
    return Template(
        "scenarios/scenario_name/procedures/procedure_index.html",
        context={
            **scenario["meta_data"],
            "index": procedure_index,
            "procedure": procedure,
            "selected_tactic": selected_tactic,
            "tactics": tactics,
            "selected_technique": selected_technique,
            "techniques": techniques,
        },
    )
