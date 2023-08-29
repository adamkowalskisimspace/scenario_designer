from litestar import get
from litestar.response import Template


@get("/")
async def get_handler() -> Template:
    return Template("index.html")
