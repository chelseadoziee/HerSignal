# HerSignal Streamlit demo

Standalone shareable UI. **Does not replace or modify** the Flask app (`app.py`).

## Run locally

```bash
cd HerSignal
source .venv/bin/activate
pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
```

Open the URL shown in the terminal (usually http://localhost:8501).

First FAQ question may take 30–60 seconds while the embedding model loads.

## Share on Streamlit Community Cloud

1. Push this repo to GitHub (include `data/`, `logic/`, `chatbot/`, `dashboard/`, `static/streamlit_custom.css`, and `streamlit_app.py`).
2. Go to [share.streamlit.io](https://share.streamlit.io) and create an app.
3. **Main file path:** `streamlit_app.py` (not `app.py`)
4. **Requirements file:** `requirements-streamlit.txt`
5. **Python version:** 3.11 (repo includes `runtime.txt` with `python-3.11.9`)

### If you see `db.create_all()` / SQLAlchemy errors

That means Cloud is running the **Flask** entry (`app.py`) instead of the Streamlit demo. In the app settings, change **Main file path** to `streamlit_app.py` and redeploy.

If you must keep `app.py` as the main file, recent versions delegate to `streamlit_app.py` when started with `streamlit run app.py`, but setting the main file correctly is still recommended.

Note: Free tier cold starts are slow because of `sentence-transformers`. The demo is best for sharing logic and copy, not sub-second chat.

## What is included vs Flask

| Feature | Streamlit demo | Flask app |
|--------|----------------|-----------|
| FAQ chat | Yes | Yes |
| Symptom checker + results | Yes | Yes |
| Chart + HerSignal copy | Yes | Yes |
| User accounts / login | No | Yes |
| Insights timeline / retake | No | Yes |
| PDF export | No | Yes |

## Files (demo only)

- `streamlit_app.py` — entry point
- `static/streamlit_custom.css` — UI theme aligned with the Flask app (pink cards, hero, journey strip)
- `requirements-streamlit.txt` — dependencies
- `.streamlit/config.toml` — pink theme

No changes are required to `app.py` to run either version.
