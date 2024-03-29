import json
from pathlib import Path
from litestar import get
from litestar.response import Template


@get("/scenarios")
async def get_handler() -> Template:
    paths = Path(".") / "scenarios"
    scenarios = []
    for path in paths.iterdir():
        with open(path) as fp:
            scenario = json.load(fp)
        scenarios.append(scenario["meta_data"])
    return Template(
        "scenarios/index.html",
        context={"scenarios": sorted(scenarios, key=lambda x: x["name"])},
    )
