import logging

# Number in %(filename){num}s corresponds to the longest .py filename in project folder
logging.basicConfig(
    format="%(asctime)s | %(filename)14s:%(lineno)3d | %(levelname)8s | %(message)s",
    level=logging.DEBUG,
)

supress_library_debug = True

if supress_library_debug:
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.INFO)
    logging.getLogger("httpcore.connection").setLevel(logging.INFO)
    logging.getLogger("httpcore.http11").setLevel(logging.INFO)
    logging.getLogger("aiohttp.server").setLevel(logging.INFO)
    logging.getLogger("aiohttp.access").setLevel(logging.INFO)
