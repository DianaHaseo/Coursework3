"""Клиенты для получения данных из Nominatim и OpenSky Network."""

import time
from typing import Any

import requests


class NominatimClient:
    """Клиент Nominatim для получения границ стран."""

    def __init__(self, user_agent: str = "aircraft-project/1.0") -> None:
        """Сохраняет User-Agent для запросов к Nominatim."""
        self._user_agent = user_agent

    def get_country_bbox(self, country_name: str) -> dict[str, Any]:
        """Получает название, код и bounding box страны.

        Args:
            country_name: Название страны на английском языке.

        Returns:
            Словарь с названием, кодом страны и границами.

        Raises:
            ValueError: Если страна не найдена или у неё нет границ.
        """
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": country_name,
                "format": "json",
                "addressdetails": "1",
                "limit": "1",
            },
            headers={"User-Agent": self._user_agent},
            timeout=30,
        )
        response.raise_for_status()

        results = response.json()

        if not results:
            raise ValueError(f"Страна не найдена: {country_name}")

        country = results[0]
        bbox = country.get("boundingbox")

        if not bbox or len(bbox) != 4:
            raise ValueError(f"Для страны не найдены границы: {country_name}")

        south, north, west, east = map(float, bbox)

        return {
            "name": country["display_name"].split(",")[0].strip(),
            "country_code": country.get("address", {}).get("country_code", "").upper(),
            "lamin": south,
            "lamax": north,
            "lomin": west,
            "lomax": east,
        }


class OpenSkyClient:
    """Клиент OpenSky Network с авторизацией OAuth2 client credentials."""

    TOKEN_URL = (
        "https://auth.opensky-network.org/auth/realms/opensky-network/"
        "protocol/openid-connect/token"
    )
    STATES_URL = "https://opensky-network.org/api/states/all"

    def __init__(self, client_id: str, client_secret: str) -> None:
        """Сохраняет учётные данные OpenSky.

        Args:
            client_id: Client ID из личного кабинета OpenSky.
            client_secret: Client Secret из личного кабинета OpenSky.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._token_expires_at: float = 0

    def _get_access_token(self) -> str:
        """Получает access token или возвращает ранее сохранённый.

        Returns:
            Действующий access token.

        Raises:
            requests.HTTPError: Если авторизация в OpenSky не удалась.
        """
        if self._token and time.time() < self._token_expires_at:
            return self._token

        response = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()

        token_data = response.json()
        self._token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 1800)

        # Обновляем токен за 30 секунд до окончания его срока действия.
        self._token_expires_at = time.time() + expires_in - 30

        return self._token

    def get_aircraft_in_bbox(self, bbox: dict[str, float]) -> list[dict[str, Any]]:
        """Получает самолёты в заданном воздушном пространстве.

        Args:
            bbox: Словарь с границами: lamin, lamax, lomin, lomax.

        Returns:
            Список словарей с данными о воздушных судах.
        """
        response = requests.get(
            self.STATES_URL,
            params=bbox,
            headers={"Authorization": f"Bearer {self._get_access_token()}"},
            timeout=30,
        )
        response.raise_for_status()

        states = response.json().get("states") or []

        return [self._parse_state(state) for state in states]

    @staticmethod
    def _parse_state(state: list[Any]) -> dict[str, Any]:
        """Преобразует state vector OpenSky в словарь.

5        Args:
            state: Массив данных об одном самолёте из ответа OpenSky.

        Returns:
            Словарь с полями для сохранения в PostgreSQL.
        """
        return {
            "icao24": state[0],
            "callsign": (state[1] or "").strip() or None,
            "origin_country": state[2],
            "time_position": state[3],
            "last_contact": state[4],
            "longitude": state[5],
            "latitude": state[6],
            "baro_altitude": state[7],
            "on_ground": state[8],
            "velocity": state[9],
            "true_track": state[10],
            "vertical_rate": state[11],
            "geo_altitude": state[13],
            "squawk": state[14],
        }