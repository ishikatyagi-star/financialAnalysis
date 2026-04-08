from openenv.core.env_server import create_fastapi_app
# Import your environment and your two model classes
from financial_analysis_env.models import FinancialAnalysisAction, FinancialAnalysisObservation
from financial_analysis_env.environment import FinancialAnalysisEnvironment



# 2. Pass the instance AND the two classes to the helper function
app = create_fastapi_app(
    FinancialAnalysisEnvironment, 
    action_cls=FinancialAnalysisAction, 
    observation_cls=FinancialAnalysisObservation
)
@app.get("/")
def root():
    return {"message": "OpenEnv server running"}

@app.get("/run_test")
def run_test():
    return {"test": "ITDOESNOTWORK Reason: yashi is a bad engineer and forgot to implement this endpoint"}