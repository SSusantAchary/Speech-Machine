# Test Steps

## 1) Prereqs
- Docker Desktop running
- Node 20+ and Python 3.11+ (only needed if running tests outside Docker)

## 2) Start the stack
```bash
cd video_record
docker compose up
```

## 3) Open the app
- Web: http://localhost:3000
- API: http://localhost:8000

## 4) Smoke test (manual)
1. Login with `admin` / `admin` (local-only default), or use /signup to create an account.
2. Go to /record and allow camera/mic permissions.
3. Click the record button, speak for 10+ seconds, then stop.
4. Click "Save session" and wait for redirect to /session/:id.
5. Confirm playback, transcript, score, and timeline markers render.

## 5) Frontend unit tests
```bash
cd video_record/apps/web
npm test
```

## 6) Frontend e2e tests (Playwright)
```bash
cd video_record/apps/web
npm run test:e2e
```

## 7) Backend tests
```bash
cd video_record/apps/api
pytest
```

## 8) Troubleshooting
- If camera/mic fails, check browser permissions and reload /record.
- If transcription fails, verify ffmpeg is available in the API container and the Whisper model downloads.
- If the API is unreachable, confirm docker compose logs for the api service.
