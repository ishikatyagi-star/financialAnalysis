import json
import gradio as gr

from .financial_analysis_environment import FinancialAnalysisOpenEnv
from financial_analysis_env.models import FinancialAnalysisAction

# We will instantiate a global env just for the UI
env = FinancialAnalysisOpenEnv()


def load_scenario(task_level: str):
    """Resets the environment with the specified task level and returns the UI updates."""
    # Reset the environment
    obs = env.reset(task=task_level.lower())
    
    # Format the data nicely
    desc = f"### Task: {obs.difficulty.upper()}\n\n{obs.task_description}"
    data_str = json.dumps(obs.financial_data, indent=2)
    
    # We clear the input/output fields
    return (
        desc, 
        data_str,
        "",  # Clear analysis
        "",  # Clear issues
        "",  # Clear recommendations
        "**Submit your analysis above to see your score.**" # Clear results
    )


def submit_analysis(analysis: str, issues: str, recommendation: str):
    """Steps the environment with the user's action and returns the reward."""
    # Convert comma-separated string to list
    issues_list = [i.strip() for i in issues.split(",") if i.strip()]
    
    action = FinancialAnalysisAction(
        analysis=analysis,
        identified_issues=issues_list,
        recommendation=recommendation
    )
    
    # Step the environment
    obs = env.step(action)
    
    # Format the result
    score = obs.reward if obs.reward is not None else 0.0
    
    result_markdown = f"""
### 📊 Grader Result
- **Score**: `{score:.4f}`
- **Range**: strictly in `(0, 1)`
- **Done**: `{obs.done}`

*Breakdown metrics usually influence this final scalar score. You can adjust your analysis and try again!*
"""
    if obs.info:
        result_markdown += f"\n\n**Details**: \n```json\n{json.dumps(obs.info, indent=2)}\n```"

    return result_markdown


def build_demo() -> gr.Blocks:
    # Custom CSS for a sleek financial look
    custom_css = """
    .gradio-container { max-width: 1200px !important; }
    .header-html { text-align: center; margin-bottom: 2rem; }
    .header-html h1 { color: #1e3a8a; }
    """
    
    with gr.Blocks(css=custom_css, title="Financial Analysis Benchmark") as demo:
        gr.HTML(
            """
            <div class="header-html">
                <h1>📈 Financial Analysis Benchmark</h1>
                <p>Play as an expert automated financial analyst. Review company financial data, 
                provide a written analysis, flag potential issues, and submit a 
                strategic recommendation to get graded.</p>
            </div>
            """
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                task_dropdown = gr.Dropdown(
                    choices=["easy", "medium", "hard"], 
                    value="easy", 
                    label="Select Scenario Difficulty"
                )
            with gr.Column(scale=1):
                load_btn = gr.Button("🔄 Load Scenario", variant="primary")
                
        with gr.Row():
            # LEFT PANEL: The Brief
            with gr.Column(scale=1):
                gr.Markdown("### 🏢 The Brief & Data")
                task_display = gr.Markdown("*(Load a scenario to see the task description)*")
                data_display = gr.Code(language="json", label="Financial Data")
                
            # RIGHT PANEL: The Workspace
            with gr.Column(scale=1):
                gr.Markdown("### ✍️ Your Analysis Workspace")
                analysis_input = gr.Textbox(
                    lines=5, 
                    label="Written Analysis", 
                    placeholder="Provide your detailed financial analysis here..."
                )
                issues_input = gr.Textbox(
                    lines=2, 
                    label="Identified Issues (comma separated)", 
                    placeholder="e.g. rising costs, declining margins"
                )
                rec_input = gr.Textbox(
                    lines=3, 
                    label="Recommendation", 
                    placeholder="What should the company do?"
                )
                submit_btn = gr.Button("🚀 Submit Analysis", variant="primary")
                
        gr.Markdown("---")
        
        with gr.Row():
            with gr.Column():
                result_display = gr.Markdown("**Submit your analysis above to see your score.**")
                
        # --- Event Wireup ---
        
        # When Load is clicked, fetch data and clear fields
        load_btn.click(
            fn=load_scenario,
            inputs=[task_dropdown],
            outputs=[
                task_display, 
                data_display, 
                analysis_input, 
                issues_input, 
                rec_input, 
                result_display
            ]
        )
        
        # When Submit is clicked, send action and display result
        submit_btn.click(
            fn=submit_analysis,
            inputs=[analysis_input, issues_input, rec_input],
            outputs=[result_display]
        )
        
        # Trigger an initial load when the app starts
        demo.load(
            fn=load_scenario,
            inputs=[task_dropdown],
            outputs=[
                task_display, 
                data_display, 
                analysis_input, 
                issues_input, 
                rec_input, 
                result_display
            ]
        )
        
    return demo
