.PHONY: run-backend run-frontend

run-backend:
	cd backend && source ../venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000

run-frontend:
	cd frontend && source ../venv/bin/activate && streamlit run app.py
