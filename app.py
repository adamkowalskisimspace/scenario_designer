from pathlib import Path
from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.static_files import StaticFilesConfig
from litestar.template.config import TemplateConfig

import routes
from routes import scenarios
from routes.scenarios import scenario_name


app = Litestar(
    route_handlers=[
        routes.get_handler,
        scenarios.get_handler,
        scenario_name.get_handler,
    ],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=JinjaTemplateEngine,
    ),
    static_files_config=[StaticFilesConfig(path="/static", directories=["static"])],
)
