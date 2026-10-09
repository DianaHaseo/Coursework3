"""Создание таблиц PostgreSQL и загрузка данных из внешних API."""

import configparser
from pathlib import Path
from typing import Any
import psycopg2
from api import NominatimClient, OpenSkyClient

CONFIG_FILE = Path("database.ini")

COUNTRIES = [
    "Germany",
    "France",
    "Spain",
    "Italy",
    "Poland",
    "United Kingdom",
    "Netherlands",
    "Switzerland",
    "Austria",
    "Portugal",
]


def get_connection() -> psycopg2.extensions.connection:
    """Создаёт подключение к PostgreSQL напрямую, минуя проблемный файл конфигурации."""
    return psycopg2.connect(
        host="localhost",
        user="postgres",
        password="u5cdc8fr",
        port=5432,
        dbname="coursework3",
    )


def create_tables(connection: psycopg2.extensions.connection) -> None:
    """Создаёт таблицы стран и воздушных судов.

    Args:
        connection: Подключение к PostgreSQL.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS countries (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                country_code VARCHAR(2),
                lamin DOUBLE PRECISION NOT NULL,
                lamax DOUBLE PRECISION NOT NULL,
                lomin DOUBLE PRECISION NOT NULL,
                lomax DOUBLE PRECISION NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS aeroplanes (
                id SERIAL PRIMARY KEY,
                icao24 VARCHAR(12) NOT NULL UNIQUE,
                callsign VARCHAR(20),
                origin_country VARCHAR(255),
                time_position BIGINT,
                last_contact BIGINT,
                longitude DOUBLE PRECISION,
                latitude DOUBLE PRECISION,
                baro_altitude DOUBLE PRECISION,
                on_ground BOOLEAN,
                velocity DOUBLE PRECISION,
                true_track DOUBLE PRECISION,
                vertical_rate DOUBLE PRECISION,
                geo_altitude DOUBLE PRECISION,
                squawk VARCHAR(10),
                country_id INTEGER REFERENCES countries(id) ON DELETE CASCADE
            );
            """
        )
    connection.commit()


def load_countries(connection: psycopg2.extensions.connection) -> None:
    """Получает данные о странах из Nominatim и сохраняет их в PostgreSQL.

    Args:
        connection: Подключение к PostgreSQL.
    """
    nominatim_client = NominatimClient()
    for country_name in COUNTRIES:
        country = nominatim_client.get_country_bbox(country_name)
        if not country:
            continue
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO countries (name, country_code, lamin, lamax, lomin, lomax)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    country_code = EXCLUDED.country_code,
                    lamin = EXCLUDED.lamin,
                    lamax = EXCLUDED.lamax,
                    lomin = EXCLUDED.lomin,
                    lomax = EXCLUDED.lomax;
                """,
                (
                    country["name"],
                    country["country_code"],
                    country["lamin"],
                    country["lamax"],
                    country["lomin"],
                    country["lomax"],
                ),
            )
    connection.commit()


def load_aircraft(connection: psycopg2.extensions.connection) -> None:
    """Получает самолёты из OpenSky и сохраняет их в PostgreSQL.

    Args:
        connection: Подключение к PostgreSQL.
    """
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE, encoding="utf-8")

    client_id = config.get("opensky", "client_id", fallback="dianahaseo-api-client")
    client_secret = config.get("opensky", "client_secret", fallback="9Dz9SGWbmWNaIJhFMvTOfiezuEoOvbrK")

    opensky_client = OpenSkyClient(
        client_id=client_id,
        client_secret=client_secret,
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, lamin, lamax, lomin, lomax
            FROM countries;
            """
        )
        countries = cursor.fetchall()

    for country_id, lamin, lamax, lomin, lomax in countries:
        aircraft_list = opensky_client.get_aircraft_in_bbox(
            {
                "lamin": lamin,
                "lamax": lamax,
                "lomin": lomin,
                "lomax": lomax,
            }
        )

        for aircraft in aircraft_list:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO aeroplanes (
                        icao24, callsign, origin_country, time_position, last_contact,
                        longitude, latitude, baro_altitude, on_ground, velocity,
                        true_track, vertical_rate, geo_altitude, squawk, country_id
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (icao24) DO UPDATE SET
                        callsign = EXCLUDED.callsign,
                        origin_country = EXCLUDED.origin_country,
                        time_position = EXCLUDED.time_position,
                        last_contact = EXCLUDED.last_contact,
                        longitude = EXCLUDED.longitude,
                        latitude = EXCLUDED.latitude,
                        baro_altitude = EXCLUDED.baro_altitude,
                        on_ground = EXCLUDED.on_ground,
                        velocity = EXCLUDED.velocity,
                        true_track = EXCLUDED.true_track,
                        vertical_rate = EXCLUDED.vertical_rate,
                        geo_altitude = EXCLUDED.geo_altitude,
                        squawk = EXCLUDED.squawk,
                        country_id = EXCLUDED.country_id;
                    """,
                    (
                        aircraft["icao24"],
                        aircraft["callsign"],
                        aircraft["origin_country"],
                        aircraft["time_position"],
                        aircraft["last_contact"],
                        aircraft["longitude"],
                        aircraft["latitude"],
                        aircraft["baro_altitude"],
                        aircraft["on_ground"],
                        aircraft["velocity"],
                        aircraft["true_track"],
                        aircraft["vertical_rate"],
                        aircraft["geo_altitude"],
                        aircraft["squawk"],
                        country_id,
                    ),
                )

    connection.commit()