import logging

# Number in %(name){num}s corresponds to the longest .py filename in project folder
logging.basicConfig(
    format="%(asctime)s | %(name)14s:%(lineno)3d | %(levelname)8s | %(message)s",
    level=logging.DEBUG,
)

supress_library_debug = True

if supress_library_debug:
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.INFO)
