from pydantic import BaseModel, Field, field_validator
from typing import Optional

class FinancialAnalysisAction(BaseModel):
    model_config = {"extra": "allow"}

    analysis: str = Field(default="", description="The AI's written analysis")
    identified_issues: list[str] = Field(default_factory=list, description="List of issues or anomalies found")
    recommendation: str = Field(default="", description="What the AI recommends")

    @field_validator("identified_issues", mode="before")
    @classmethod
    def coerce_to_list(cls, v):
        """Accept a plain string (e.g. from Gradio textarea) and split into list items."""
        if isinstance(v, str):
            # Split on newlines or semicolons; fall back to wrapping the whole string
            import re
            items = [s.strip() for s in re.split(r'[\n;]', v) if s.strip()]
            return items if items else []
        return v


class FinancialAnalysisObservation(BaseModel):
    model_config = {"extra": "allow"}

    task_description: str = Field(default="", description="What the AI needs to do")
    financial_data: dict = Field(default_factory=dict, description="The financial data to analyze")
    difficulty: str = Field(default="easy", description="easy, medium, or hard")
    done: bool = Field(default=False, description="Whether the episode is finished")
    # None on reset (no action taken yet); float in (0,1) after step()
    reward: Optional[float] = Field(default=None, description="The reward for the last action")
    info: dict = Field(default_factory=dict, description="Additional breakdown information")