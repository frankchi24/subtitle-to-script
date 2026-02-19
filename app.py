from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from processor import process_subtitle_bytes

app = FastAPI()
templates = Jinja2Templates(directory="templates")

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/process")
async def process(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    filename = file.filename or "upload.srt"
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ('srt', 'ass'):
        raise HTTPException(status_code=400, detail="Only .srt and .ass files are supported")

    try:
        result = process_subtitle_bytes(content, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Processing error: {str(e)}")

    return {"text": result}
