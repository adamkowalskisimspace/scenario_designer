from pathlib import Path
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.static_files import StaticFilesConfig
from litestar.template.config import TemplateConfig

import routes
from routes import scenarios
from routes.scenarios import scenario_name
from routes.scenarios.scenario_name import (
    meta_data,
    procedures,
    indicators_of_compromise,
)
from routes.scenarios.scenario_name.procedures import procedure_index
from routes.scenarios.scenario_name.indicators_of_compromise import indicator


app = Litestar(
    route_handlers=[
        routes.get_handler,
        scenarios.get_handler,
        scenario_name.get_handler,
        meta_data.get_handler,
        procedures.get_handler,
        procedure_index.get_handler,
        indicators_of_compromise.get_handler,
        indicator.get_handler,
    ],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=JinjaTemplateEngine,
    ),
    static_files_config=[StaticFilesConfig(path="/static", directories=["static"])],
)
