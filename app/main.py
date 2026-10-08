from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Análisis de solicitudes", lifespan=lifespan)
