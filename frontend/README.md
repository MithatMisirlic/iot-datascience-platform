# Streamlit Frontend

The `frontend` package contains the Streamlit dashboard for operating the IoT Data Science Platform through the existing FastAPI REST API.

The dashboard does not import backend database code, Raspberry Pi code, or processing internals. It communicates only through HTTP using `frontend/api_client.py`.

## Pages

- Dashboard: backend health, API base URL, experiment count, and exercise count.
- Experiments: create, list, edit, and delete experiments.
- Exercises: create, list, inspect, and delete exercises under an experiment.
- Recording: start and stop backend recording lifecycle state for an exercise.
- Live Experiment: guided recording workflow with Pi connection status, sensor frame rates, latest IMU/audio/mouth values, and throttled camera preview.
- Results: fetch persisted `ExerciseData`, display charts/aggregates, and clear data.

The normal dashboard workflow starts/stops recording through the backend. On stop, the backend persists buffered raw frames and runs processing automatically. The CLI remains available only as a fallback/debug tool.

## Presentation Features

- Experiment Summary cards show the selected experiment, exercise, recording status, Pi connection, duration, processing state, and timestamps.
- Live Monitoring uses sensor status badges, tabs, rolling charts, and user-friendly empty states for disconnected sensors.
- Results use Speech, Movement, Vision, and Overall tabs with metric cards and Plotly-capable charts.
- Research Summary exports a descriptive Markdown report with explicit non-diagnostic limitations.
- ProcessedResult JSON and chart-series CSV exports are available from the Results page.
- Demo mode can load the latest processed exercise when no Pi is connected.

## Setup

From the repository root on the development machine:

```bash
python -m pip install -r requirements.txt
python -m pip install -r frontend/requirements.txt
```

Optional local environment file:

```bash
cp frontend/.env.example frontend/.env
```

Windows PowerShell:

```powershell
Copy-Item frontend/.env.example frontend/.env
```

Streamlit does not automatically load `frontend/.env` in every shell. You can also set `API_BASE_URL` in the shell or use the sidebar API URL field.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `API_BASE_URL` | `http://localhost:3000` | FastAPI backend base URL. |
| `API_TIMEOUT_SECONDS` | `10` | HTTP timeout used by the frontend API client. |

Plotly is listed as the preferred chart dependency. The chart helpers fall back to Streamlit-native charts if Plotly is unavailable.

## Start the Backend

From the repository root:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 3000
```

Verify:

```text
http://localhost:3000/health
http://localhost:3000/docs
```

## Start Streamlit

From the repository root:

```bash
streamlit run frontend/app.py
```

Open:

```text
http://localhost:8501
```

Do not run `python frontend/app.py`. The Streamlit command is required.

## Demonstration Workflow

1. Open the dashboard and confirm backend health.
2. Create an experiment.
3. Create an exercise under that experiment.
4. Open the Live Experiment page.
5. Select the experiment and exercise.
6. Start recording.
7. Confirm Pi connection status, frame rates, latest sensor values, and optional camera preview.
8. Perform the exercise task.
9. Stop recording and wait for automatic processing to finish.
10. Return to the Results page, select the same exercise, and click **Fetch processed data**.

Fallback/debug processing remains available from the repository root:

```bash
python -m tools.process_exercise <exercise-id> --generate-sample
```

Replace `<exercise-id>` with the real exercise UUID from the dashboard.

## Result Display Notes

- `mouthOpening`, `soundPressure`, `footSpeed`, and `aggregates` are rendered defensively.
- Extended analysis metadata is rendered when present, including MFCC summaries, syllable count, clarity proxy, steps, cadence, tremor frequency, MAR, jaw movement, completeness, and cross-modal statistics.
- Missing or empty result sections show an empty state instead of crashing.
- Foot speed is labeled as an acceleration-derived research placeholder.
- The dashboard does not provide medical diagnosis or clinical interpretation.

## Import Path Troubleshooting

If you see:

```text
ModuleNotFoundError: No module named 'frontend'
```

Confirm you are running from the repository root:

```bash
streamlit run frontend/app.py
```

The app and native page modules include a minimal path bootstrap for Streamlit execution, so users should not need to set `PYTHONPATH` manually.

## Other Troubleshooting

- Backend unavailable: start `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 3000` and check `/health`.
- Wrong backend URL: set `API_BASE_URL` or update the sidebar value.
- No results: stop recording from Live Experiment and wait for automatic processing; if processing failed, retry with `python -m tools.process_exercise <exercise-id>` using the real UUID.
- Exercise not found: replace `<exercise-id>` with a real UUID from the dashboard/API.
- Browser still showing old UI: refresh the page or stop and restart Streamlit.

## Tests

Frontend-focused tests are included under `tests/frontend/`. From the repository root:

```bash
python -m pytest tests/frontend -q
```

Full project tests:

```bash
python -m pytest -q
```
