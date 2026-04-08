---
title: Financial Analysis Environment
emoji: 📈
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Financial Analysis Environment (OpenEnv)

## Description & Motivation
This environment is designed to evaluate an AI agent's ability to perform quantitative and qualitative financial analysis. In real-world finance, professionals must sift through raw data (P&L statements, revenue logs, and growth metrics) to identify anomalies, calculate KPIs, and suggest strategic actions. 

The **motivation** for this environment is to provide a standardized benchmark for LLMs to prove they can move beyond simple text summarization and perform actual "Financial Reasoning"—linking numerical changes to business risks.

---

## Action & Observation Space

### Observation Space
The observation is a JSON object (`FinancialAnalysisObservation`) containing:
* **task_description**: A string explaining the specific financial query.
* **financial_data**: A dictionary containing the raw numbers (Quarterly/Monthly/Annual data).
* **difficulty**: A categorical label (`easy`, `medium`, or `hard`).
* **done**: A boolean indicating if the episode has finished.
* **reward**: The score achieved in the previous step (0.0 to 1.0).

### Action Space
The agent must provide a structured response (`FinancialAnalysisAction`):
* **analysis**: A detailed string explaining the mathematical reasoning.
* **identified_issues**: A list of strings identifying specific anomalies or data points (e.g., "Q2", "Month 8").
* **recommendation**: A string suggesting a business action based on the analysis.

---

## Task Descriptions & Difficulty

| Difficulty | Task Name | Description |
| :--- | :--- | :--- |
| **Easy** | Revenue Growth | Calculate QoQ growth and identify the highest growth quarter. |
| **Medium** | P&L Anomaly | Detect a specific cost spike in a 12-month expense sequence. |
| **Hard** | Multi-year Risk | Analyze 3-year trends in Gross Margin, OPEX, and CAC to identify 3 distinct business risks. |

---

## Setup & Usage

### Local Development
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install .
   ```
3. Run the server:
   ```bash
   uvicorn financial_analysis_env.server.app:app --port 7860
   ```

### API Usage
Once the Space is running, you can interact with it via POST requests:
* **Reset**: `POST /reset` with payload `{"episode_id": "test-001", "seed": 42}`
* **Step**: `POST /step` with your `FinancialAnalysisAction` payload.

---

## Baseline Scores

These scores represent the performance of a standard LLM (e.g., GPT-4o or Claude 3.5 Sonnet) using a zero-shot prompt, we ave used Qwen/Qwen2.5-72B-Instruct:

* **Easy Task**: 1.0 (High accuracy on percentage calculations).
* **Medium Task**: 0.7 - 0.9 (Occasionally misses the specific month naming convention).
* **Hard Task**: 0.5 - 0.8 (Requires strong chain-of-thought to link CAC increases to margin compression).
* **Average Baseline**: **0.82**