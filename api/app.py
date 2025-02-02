import sys
import os
import shutil
from tempfile import NamedTemporaryFile
from pathlib import Path
from fastapi.responses import FileResponse
from googletrans import Translator

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

@app.post("/detect/")
async def detect_uploaded_file(file: UploadFile):
    filename = file.filename

    processor = None
    fileType = ""

    if filename.lower().endswith(".gridset"):
        processor = GridsetProcessor()
        fileType = "Grid3"

    if processor is not None:
        gridset_file = save_upload_file_tmp(file)
        texts = processor.extract_texts(gridset_file)
        translator = Translator()
        response = await translator.detect(texts)

        langMap = {}

        for detected in response:
            # print(detected.lang, detected.confidence)
            if detected.lang in langMap:
                langMap[detected.lang] += detected.confidence
            else:
                langMap[detected.lang] = detected.confidence

        sourceLang = max(langMap, key=langMap.get)

        return {
            "sourceFiletype": fileType,
            "sourceLanguage": sourceLang
        }

    return {
        "sourceLanguage": "unknown",
        "sourceFiletype": "unknown"
    }

@app.post("/upload/")
async def create_upload_file(file: UploadFile, sourceLang: str, targetLang: str, fileType: str):
    processor = GridsetProcessor()

    processor = None

    if fileType.lower() == "grid3":
        processor = GridsetProcessor()

    if processor is None:
        return {
            "error": "Unsupported file type"
        }

    gridset_file = save_upload_file_tmp(file)
    texts = processor.extract_texts(gridset_file)

    translator = Translator()
    translated = await translator.translate(texts, src=sourceLang, dest=targetLang)

    translations = {}
    for i, text in enumerate(texts):
        translations[text] = translated[i].text
    
    translations["target_lang"] = targetLang

    translated_file = processor.create_translated_file(gridset_file, translations)

    return FileResponse(translated_file, media_type="application/octet-stream")