import datetime
import json
from contextlib import asynccontextmanager
from dataclasses import asdict

import asqlite
from fastapi import FastAPI, HTTPException

from .metadata import OpenGraphBaseData, OpenGraphImageData, OpenGraphTextData, OpenGraphVideoData
from .utils import find_provider

__all__ = ("ensure_database", "lifespan", "cache_data")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with asqlite.connect("cache.db") as conn:
        await ensure_database(conn)
    yield


async def ensure_database(conn: asqlite.Connection):
    with open("./schema.sql") as fp:
        sql = fp.read()
    async with conn.cursor() as cursor:
        await cursor.executescript(sql)
        await conn.commit()


async def cache_data(conn: asqlite.Connection, info: OpenGraphBaseData, url: str):
    # Yes, i know this is cursed. But I'm lazy.
    async with conn.cursor() as cursor:
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        await cursor.execute(
            "INSERT INTO cache(url, data, expiry, type) VALUES(?, ?, ?, ?)",
            url,
            json.dumps(asdict(info)),
            tomorrow.timestamp(),
            info.to_type(),
        )


async def get_and_cache(conn: asqlite.Connection, url: str) -> OpenGraphBaseData:
    info = await try_cache(conn, url)
    if info:
        return info

    provider = find_provider(url)
    if not provider:
        raise HTTPException(404)

    return await provider.parse(url)


async def try_cache(conn: asqlite.Connection, url: str) -> OpenGraphBaseData | None:
    async with conn.cursor() as cursor:
        res = await cursor.execute("SELECT * FROM cache WHERE url = ?", url)
        row = await res.fetchone()
        if not row:
            return None

        data_type: str = row["type"]
        data = json.loads(row["data"])
        match data_type:
            case "video":
                return OpenGraphVideoData(**data)
            case "text":
                return OpenGraphTextData(**data)
            case "image":
                return OpenGraphImageData(**data)
            case _:
                raise Exception("Invalid data type.")  # noqa: TRY002, TRY003
