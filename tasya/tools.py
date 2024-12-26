from typing import Any

import requests

from tasya.config import config

def tavily_search(query: str) -> list[str]:
    resp = requests.post("https://api.tavily.com/search", json={"query": query, "api_key": config.tavily_token})
    js = resp.json()
    res = [r["content"] for r in js["results"]]
    return res

def owm_current_weather(lat: float, lon: float) -> dict[str, Any]:
    resp = requests.get("https://api.openweathermap.org/data/2.5/weather", params={"lat": lat, "lon": lon, "appid": config.owm_token, "units": "metric"})
    js = resp.json()
    res = {}
    res["weather"] = js["weather"][0]["description"]
    res["temp"] = js["main"]["temp"]
    res["wind"] = js["wind"]["speed"]
    return res

def loc_by_str(query: str) -> tuple[float]:
    resp = requests.get("https://geocode-maps.yandex.ru/1.x/", params={"apikey": config.ymaps_token, "geocode": query, "format": "json"})
    js = resp.json()
    addr = js["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    lat = float(addr["Point"]["pos"].split(" ")[1])
    lon = float(addr["Point"]["pos"].split(" ")[0])
    return lat, lon
