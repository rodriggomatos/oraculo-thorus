cd C:\Python\oraculo-thorus\apps\api
uv run uvicorn oraculo_api.main:app --reload --port 8000

cd C:\Python\oraculo-thorus
.\apps\api\scripts\dev.ps1

cd C:\Python\oraculo-thorus\apps\web
npm run dev