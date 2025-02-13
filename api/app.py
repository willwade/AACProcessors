import sys
import os
import shutil
import json
from tempfile import NamedTemporaryFile
from pathlib import Path
from fastapi.responses import FileResponse
from google.cloud import translate_v2 as translate
from google.oauth2 import service_account

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, File, UploadFile
from aac_processors import GridsetProcessor, TouchChatProcessor, SnapProcessor, CoughDropProcessor

app = FastAPI()

gcloud_creds = os.getenv('GCLOUD_CREDS')
if gcloud_creds:
    creds_dict = json.loads(gcloud_creds)
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    translate_client = translate.Client(credentials=credentials)
else:
    raise EnvironmentError("GCLOUD_CREDS environment variable not set or invalid")

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
        fileType = "GridsetProcessor"

    if filename.lower().endswith(".obz"):
        processor = CoughDropProcessor()
        fileType = "CoughDropProcessor"

    if filename.lower().endswith(".sps"):
        processor = SnapProcessor()
        fileType = "SnapProcessor"

    if filename.lower().endswith(".ce"):
        processor = TouchChatProcessor()
        fileType = "TouchChatProcessor"

    if processor is not None:
        gridset_file = save_upload_file_tmp(file)

        try:
            texts = processor.extract_texts(gridset_file)
            response = [translate_client.detect_language(text) for text in texts]

            langMap = {}

            for detected in response:
                lang = detected['language']
                confidence = detected['confidence']
                if lang in langMap:
                    langMap[lang] += confidence
                else:
                    langMap[lang] = confidence

            sourceLang = max(langMap, key=langMap.get)

            return {
                "sourceFiletype": fileType,
                "sourceLanguage": sourceLang
            }
        except:
            print("Error detecting language")
            return {
                "sourceLanguage": "unknown",
                "sourceFiletype": "unknown"
            }
        

    return {
        "sourceLanguage": "unknown",
        "sourceFiletype": "unknown"
    }

@app.post("/upload/")
async def create_upload_file(file: UploadFile, sourceLang: str, targetLang: str, fileType: str):
    processor = GridsetProcessor()

    processor = None

    if fileType.lower() == "GridsetProcessor":
        processor = GridsetProcessor()
        
    if fileType.lower() == "TouchChatProcessor":
        processor = TouchChatProcessor()

    if fileType.lower() == "SnapProcessor":
        processor = SnapProcessor()

    if fileType.lower() == "CoughDropProcessor":
        processor = CoughDropProcessor()

    if processor is None:
        return {
            "error": "Unsupported file type"
        }

    gridset_file = save_upload_file_tmp(file)
    texts = processor.extract_texts(gridset_file)

    translations = {}
    for text in texts:
        result = translate_client.translate(text, source_language=sourceLang, target_language=targetLang)
        translations[text] = result['translatedText']
    
    translations["target_lang"] = targetLang

    translated_file = processor.create_translated_file(gridset_file, translations)

    return FileResponse(translated_file, media_type="application/octet-stream")