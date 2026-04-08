from fastapi import APIRouter
from openenv.core.env_server import create_fastapi_app
# Import your environment and your two model classes
from financial_analysis_env.models import FinancialAnalysisAction, FinancialAnalysisObservation
from financial_analysis_env.environment import FinancialAnalysisEnvironment

custom_router = APIRouter()

@custom_router.get("/run_test")
def run_test():
    return {"status": "success", "message": "The endpoint finally works!"}

# 2. Pass the instance AND the two classes to the helper function
app = create_fastapi_app(
    FinancialAnalysisEnvironment, 
    action_cls=FinancialAnalysisAction, 
    observation_cls=FinancialAnalysisObservation,
    root_path="/web"
)
app.root_path = "/web"  # Ensure the root path is set for the app
app.include_router(custom_router)
@app.get("/")
def root():
    return {"message": "OpenEnv server running"}
