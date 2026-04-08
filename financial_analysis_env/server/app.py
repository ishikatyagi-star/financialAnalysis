from fastapi import APIRouter
from openenv.core.env_server import create_fastapi_app
from financial_analysis_env.models import FinancialAnalysisAction, FinancialAnalysisObservation
from financial_analysis_env.environment import FinancialAnalysisEnvironment

# 1. Define your custom routes in a dedicated Router
custom_router = APIRouter()

@custom_router.get("/run_test")
def run_test():
    return {"status": "success", "message": "YES I WASTED SO MUCH TIME ON THIS! THE URL WAS WRONG! YASHI DID NOT KNOW WHAT FORMAT URL YOU WERE SUPPOSED TO USE!"}

# 2. Create the app instance
env_instance = FinancialAnalysisEnvironment
app = create_fastapi_app(
    env_instance, 
    action_cls=FinancialAnalysisAction, 
    observation_cls=FinancialAnalysisObservation
)

# 3. FORCE include the router and reset documentation
app.include_router(custom_router)

# This line is CRITICAL for Hugging Face Spaces specifically
# It forces FastAPI to re-scan for the new /run_test route
app.openapi_schema = None 

@app.get("/")
def root():
    return {"message": "OpenEnv server running"}
