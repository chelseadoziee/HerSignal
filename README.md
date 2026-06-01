## HerSignal

HerSignal is a Flask-based educational PCOS support app with:
- FAQ chatbot support
- symptom checker (yes/no/maybe)
- hormonal/metabolic/inflammatory scoring
- chart and PDF export

## Setup

```bash
cd HerSignal
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The first startup may take a moment while the FAQ model loads in the background.

Install the Python dependencies from `requirements.txt` before running the app. Those packages are not bundled with the repository; you need to download and install them in your environment first, or HerSignal will not start.

### Accounts & insights

- **Register** or **Log in** to save symptom-check snapshots and use **Insights** (timeline, retake test).
- A local SQLite database is created at `instance/hersignal.sqlite` (not committed to git).
- Session signing uses `instance/.secret_key` (created automatically; also not committed).

## FAQ dataset format

The FAQ loader supports a backward-compatible CSV schema in `data/pcos_qa.csv`.

Required columns:
- `question`
- `answer`
- `category`

Optional columns:
- `intent_id` (recommended): groups multiple phrasing variants under one intent
- `variant_group` (optional label for data curation)
- `status` (`active` or `inactive`, defaults to `active`)

If `intent_id` is missing, the matcher auto-generates one from the question text.
During ranking, the system keeps the highest-scoring candidate per `intent_id` so
new variants can be added without destabilizing final response selection.
