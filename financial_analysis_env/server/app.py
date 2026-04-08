from openenv.core.env_server import create_fastapi_app
from financial_analysis_env.models import FinancialAnalysisAction, FinancialAnalysisObservation
from financial_analysis_env.environment import FinancialAnalysisEnvironment

# 1. Create the instance
env_instance = FinancialAnalysisEnvironment()

# 2. Generate the app
app = create_fastapi_app(
    env_instance, 
    action_cls=FinancialAnalysisAction, 
    observation_cls=FinancialAnalysisObservation
)

@app.get("/")
def root():
    return {"message": "OpenEnv server running"}

@app.get("/run_test")
def run_test():
    """
    Test the environment by performing a reset and one step.
    """
    try:
        # Reset the environment to get a task
        initial_obs = env_instance.reset()
        
        # Create a dummy action to test the step function
        test_action = FinancialAnalysisAction(
            analysis="This is a test analysis of the provided financial data.",
            identified_issues=["test_issue"],
            recommendation="Perform a deeper audit of the Q2 growth."
        )
        
        # Perform one step
        step_result = env_instance.step(test_action)
        
        return {
            "status": "success",
            "initial_task": initial_obs.task_description[:50] + "...",
            "reward_received": step_result.reward,
            "done": step_result.done
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}
