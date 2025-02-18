import logging
from typing import Any

import requests

from tasya.config import config

log = logging.getLogger("tasya.tools")


class Tools:
    def __init__(self, request_id: str = "unknwn"):
        self.request_id = request_id

    def tavily_search(self, query: str) -> list[str]:
        log.info(f"Request {self.request_id}: searching the web")
        log.debug(f'req {self.request_id}: query is "{query}"')
        resp = requests.post("https://api.tavily.com/search", json={"query": query, "api_key": config.tavily_token})
        js = resp.json()
        log.debug(f"req {self.request_id}: tavily resp is {js}")
        res = [r["content"] for r in js["results"]]
        return res

    def owm_current_weather(self, lat: float, lon: float) -> dict[str, Any]:
        log.info(f"Request {self.request_id}: fetching the weather")
        log.debug(f'req {self.request_id}: location is {lat}, {lon}')
        resp = requests.get("https://api.openweathermap.org/data/2.5/weather", params={"lat": lat, "lon": lon, "appid": config.owm_token, "units": "metric"})
        js = resp.json()
        log.debug(f"req {self.request_id}: owm resp is {js}")
        res = {}
        res["weather"] = js["weather"][0]["description"]
        res["temp"] = js["main"]["temp"]
        res["wind"] = js["wind"]["speed"]
        log.debug(f"req {self.request_id}: weather info is {res}")
        return res

    def loc_by_str(self, query: str) -> tuple[float]:
        log.info(f"Request {self.request_id}: converting location to coordinates")
        log.debug(f'req {self.request_id}: location is "{query}"')
        resp = requests.get("https://geocode-maps.yandex.ru/1.x/", params={"apikey": config.ymaps_token, "geocode": query, "format": "json"})
        js = resp.json()
        log.debug(f"req {self.request_id}: yandex resp is {js}")
        addr = js["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
        lat = float(addr["Point"]["pos"].split(" ")[1])
        lon = float(addr["Point"]["pos"].split(" ")[0])
        log.debug(f"req {self.request_id}: coordinates are {lat}, {lon}")
        return lat, lon
