import random
from uuid import uuid4
from financial_analysis_env.models import (
    FinancialAnalysisAction,
    FinancialAnalysisObservation,
)
from fastapi import FastAPI
from financial_analysis_env.environment import FinancialAnalysisEnvironment

app = FastAPI()

env = FinancialAnalysisEnvironment()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset():
    obs = env.reset()

    return {
        "observation": obs.model_dump(),
        "reward": 0.0,
        "done": False
    }


@app.post("/step")
def step(action: FinancialAnalysisAction):
    return env.step(action)