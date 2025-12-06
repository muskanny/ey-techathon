# AI Personal Loan Assistant – EY Techathon

Streamlit + LangChain/LangGraph prototype showcasing the promised multi-agent personal loan journey (sales, KYC, underwriting, sanction letter). The repo currently contains the scaffolding with real orchestration so we can plug in richer logic step-by-step.

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."  # or create a .env file
python - <<'PY'
from app.services.db import init_db
init_db()
PY
streamlit run app/main.py
```

## Repo layout

- `app/main.py` – Streamlit entrypoint with chat UI + phase/status view.
- `app/state.py` – Session state model + phase machine helpers.
- `app/agents/` – LangChain tools and master orchestrator (sales, KYC, underwriting, sanction).
- `app/services/db.py` – Lightweight SQLite wrapper + seed data.
- `app/services/products.py` – Product recommendation queries.
- `app/services/` – Reserved for mock KYC, underwriting, and PDF helpers.
- `data/` – Mock databases / fixtures.
- `artifacts/` – Generated assets like sanction letters.

The Sales agent parses user intents via the LLM, queries the SQLite catalog, and captures structured loan requests. The KYC agent now validates PAN/DOB/phone against the same DB with LangChain structured extraction. Next steps will wire real underwriting and sanction logic.
