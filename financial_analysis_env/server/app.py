from fastapi import APIRouter
from openenv.core.env_server import create_fastapi_app
# Import your environment and your two model classes
from financial_analysis_env.models import FinancialAnalysisAction, FinancialAnalysisObservation
from financial_analysis_env.environment import FinancialAnalysisEnvironment

# 2. Pass the instance AND the two classes to the helper function
app = create_fastapi_app(
    FinancialAnalysisEnvironment, 
    action_cls=FinancialAnalysisAction, 
    observation_cls=FinancialAnalysisObservation,
    
)
app.root_path = "/web"

# 3. Manually add your custom route so it can't be missed
def run_test_endpoint():
    return {"status": "success", "message": "Endpoint finally reached!"}

app.add_api_route("/run_test", run_test_endpoint, methods=["GET"])

@app.get("/")
def root():
    return {"message": "OpenEnv server running"}
