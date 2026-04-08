from pydantic import BaseModel, Field

class FinancialAnalysisAction(BaseModel):
    model_config = {"extra": "allow"}

    analysis: str = Field(default="", description="The AI's written analysis")
    identified_issues: list[str] = Field(default_factory=list, description="List of issues or anomalies found")
    recommendation: str = Field(default="", description="What the AI recommends")


class FinancialAnalysisObservation(BaseModel):
    model_config = {"extra": "allow"}

    task_description: str = Field(default="", description="What the AI needs to do")
    financial_data: dict = Field(default_factory=dict, description="The financial data to analyze")
    difficulty: str = Field(default="easy", description="easy, medium, or hard")
    done: bool = Field(default=False, description="Whether the episode is finished")
    reward: float = Field(default=0.0, description="The reward for the last action")