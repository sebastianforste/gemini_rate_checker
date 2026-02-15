# Gemini Rate Checker

CLI utility that tests Gemini model `generateContent` endpoints, stores run history, and produces optional JSON/HTML reports.

## Quick Start

1. Install dependencies:
   ```bash
   python -m pip install -r requirements.lock
   ```
2. Configure `.env` in this directory:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```
3. Run a check:
   ```bash
   python gemini_rate_checker.py
   ```

## Useful CLI Options

- Save structured output for automation:
  ```bash
  python gemini_rate_checker.py --json-out ./out/latest.json
  ```
- Skip HTML dashboard generation:
  ```bash
  python gemini_rate_checker.py --no-html
  ```

## Test Command

```bash
pytest -q
```

## Deployment Notes

- For recurring checks, run this script via `cron` or CI and persist `--json-out` artifacts.
- The script writes local history to `gemini_rate_history.json` and HTML output to `gemini_rate_check_results.html`.

## Troubleshooting

- `429` responses indicate quota/rate limits, not necessarily endpoint outage.
- If all calls fail immediately, verify `GEMINI_API_KEY` and account permissions.
- If output parsing in downstream tooling fails, use `--json-out` and consume the generated JSON payload directly.
