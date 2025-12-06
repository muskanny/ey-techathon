# AI Personal Loan Assistant – EY Techathon

Streamlit + LangChain/LangGraph prototype showcasing the promised multi-agent personal loan journey (sales, KYC, underwriting, sanction letter). The repo currently contains the scaffolding with real orchestration so we can plug in richer logic step-by-step.

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."  # or create a .env file
streamlit run app/main.py
```

## Repo layout

- `app/main.py` – Streamlit entrypoint with chat UI + phase/status view.
- `app/state.py` – Session state model + phase machine helpers.
- `app/agents/` – LangChain tools and master orchestrator.
- `app/services/` – Reserved for mock KYC, underwriting, and PDF helpers.
- `data/` – Mock databases / fixtures.
- `artifacts/` – Generated assets like sanction letters.

We will expand each module in the upcoming steps (sales agent, KYC, underwriting, sanction letter generation, and final polish).
