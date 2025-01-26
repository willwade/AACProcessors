import sys
import os
import shutil
from tempfile import NamedTemporaryFile
from pathlib import Path
from fastapi.responses import FileResponse

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, File, UploadFile
from aac_processors import GridsetProcessor

app = FastAPI()

def save_upload_file_tmp(upload_file: UploadFile) -> Path:
    try:
        suffix = Path(upload_file.filename).suffix
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload_file.file, tmp)
            tmp_path = Path(tmp.name)
    finally:
        upload_file.file.close()
    return tmp_path

@app.post("/upload/")
async def create_upload_file(file: UploadFile):
    processor = GridsetProcessor()

    gridset_file = save_upload_file_tmp(file)
    texts = processor.extract_texts(gridset_file)

    translations = {}
    for i, text in enumerate(texts):
        translations[text] = f"Translated_{i}"
    translations["target_lang"] = "es"

    translated = processor.create_translated_file(gridset_file, translations)

    return FileResponse(translated, media_type="application/octet-stream")