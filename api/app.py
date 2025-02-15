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

def batchDetectLanguage(texts):
    batch_size = 128
    langMap = {}
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        results = translate_client.detect_language(batch)
        for result in results:
            lang = result['language']
            confidence = result['confidence']
            if lang in langMap:
                langMap[lang] += confidence
            else:
                langMap[lang] = confidence
    return max(langMap, key=langMap.get)

@app.post("/detect/")
async def detect_uploaded_file(file: UploadFile):
    filename = file.filename

    processor = None
    fileType = ""

    if filename.lower().endswith(".gridset"):
        processor = GridsetProcessor()
        fileType = "GridsetProcessor"

    if filename.lower().endswith(".sps") or filename.lower().endswith(".spb"):
        processor = SnapProcessor()
        fileType = "SnapProcessor"

    if filename.lower().endswith(".ce"):
        processor = TouchChatProcessor()
        fileType = "TouchChatProcessor"

    if processor is not None:
        gridset_file = save_upload_file_tmp(file)

        try:
            texts = processor.extract_texts(gridset_file)
            sourceLanguage = batchDetectLanguage(texts)

            return {
                "sourceFiletype": fileType,
                "sourceLanguage": sourceLanguage
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

def translateBatch(texts, sourceLanguage, targetLanguage):
    translations = {}
    batch_size = 128
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        results = translate_client.translate(batch, source_language=sourceLanguage, target_language=targetLanguage)
        for j, result in enumerate(results):
            translations[batch[j]] = result['translatedText']
    return translations

@app.post("/upload/")
async def create_upload_file(file: UploadFile, sourceLanguage: str, targetLanguage: str, fileType: str):
    processor = GridsetProcessor()

    processor = None

    if fileType.lower() == "GridsetProcessor".lower():
        processor = GridsetProcessor()
        
    if fileType.lower() == "TouchChatProcessor".lower():
        processor = TouchChatProcessor()

    if fileType.lower() == "SnapProcessor".lower():
        processor = SnapProcessor()

    if processor is None:
        return {
            "error": "Unsupported file type"
        }

    if sourceLanguage == targetLanguage:
        return {
            "error": "Source and target languages are the same"
        }
    
    gridset_file = save_upload_file_tmp(file)
    texts = processor.extract_texts(gridset_file)

    translations = translateBatch(texts, sourceLanguage, targetLanguage)

    # testResult = translate_client.translate(texts[:128], source_language=sourceLang, target_language=targetLang)

    # print(testResult)
    # => [{'translatedText': 'edificio', 'input': 'building'}, {'translatedText': 'edificio', 'input': 'building'}, {'translatedText': 'lugar', 'input': 'place'}, {'translatedText': 'lugar', 'input': 'place'}, {'translatedText': 'banco', 'input': 'bank'}, {'translatedText': 'banco', 'input': 'bank'}, {'translatedText': 'callejón de bolos', 'input': 'bowl alley'}, {'translatedText': 'bolera', 'input': 'bowling alley'}, {'translatedText': 'iglesia', 'input': 'church'}, {'translatedText': 'iglesia', 'input': 'church'}, {'translatedText': 'doctor', 'input': 'doctor'}, {'translatedText': 'consultorio médico', 'input': "doctor's office"}, {'translatedText': 'tienda de comestibles', 'input': 'grocery'}, {'translatedText': 'tienda de comestibles', 'input': 'grocery store'}, {'translatedText': 'centro comercial', 'input': 'shopping centre'}, {'translatedText': 'centro comercial', 'input': 'shopping centre'}, {'translatedText': 'película', 'input': 'movie'}, {'translatedText': 'película', 'input': 'movie'}, {'translatedText': 'comercio', 'input': 'shop'}, {'translatedText': 'comercio', 'input': 'shop'}, {'translatedText': 'casa', 'input': 'house'}, {'translatedText': 'casa', 'input': 'house'}, {'translatedText': 'baño', 'input': 'bathroom'}, {'translatedText': 'baño', 'input': 'bathroom'}, {'translatedText': 'cama', 'input': 'bed'}, {'translatedText': 'cama', 'input': 'bed'}, {'translatedText': 'cocina', 'input': 'kitchen'}, {'translatedText': 'cocina', 'input': 'kitchen'}, {'translatedText': 'afuera', 'input': 'outside'}, {'translatedText': 'afuera', 'input': 'outside'}, {'translatedText': 'playa', 'input': 'beach'}, {'translatedText': 'playa', 'input': 'beach'}, {'translatedText': 'acampar', 'input': 'camp'}, {'translatedText': 'acampar', 'input': 'camp'}, {'translatedText': 'granja', 'input': 'farm'}, {'translatedText': 'granja', 'input': 'farm'}, {'translatedText': 'lago', 'input': 'lake'}, {'translatedText': 'lago', 'input': 'lake'}, {'translatedText': 'océano', 'input': 'ocean'}, {'translatedText': 'océano', 'input': 'ocean'}, {'translatedText': 'parque', 'input': 'park'}, {'translatedText': 'parque', 'input': 'park'}, {'translatedText': 'patio de juegos', 'input': 'playgrnd'}, {'translatedText': 'patio de juegos', 'input': 'playground'}, {'translatedText': 'piscina', 'input': 'pool'}, {'translatedText': 'piscina', 'input': 'pool'}, {'translatedText': 'zoo', 'input': 'zoo'}, {'translatedText': 'zoo', 'input': 'zoo'}, {'translatedText': 'escuela', 'input': 'school'}, {'translatedText': 'escuela', 'input': 'school'}, {'translatedText': 'autobús', 'input': 'bus'}, {'translatedText': 'autobús', 'input': 'bus'}, {'translatedText': 'clase', 'input': 'class'}, {'translatedText': 'clase', 'input': 'class'}, {'translatedText': '?', 'input': '?'}, {'translatedText': '?', 'input': '?'}, {'translatedText': 'GRUPOS', 'input': 'GROUPS'}, {'translatedText': 'Rest&#39;rant (restante)', 'input': "rest'rant"}, {'translatedText': 'restaurante', 'input': 'restaurant'}, {'translatedText': 'el', 'input': 'the'}, {'translatedText': 'el', 'input': 'the'}, {'translatedText': 'a', 'input': 'a'}, {'translatedText': 'a', 'input': 'a'}, {'translatedText': 'y', 'input': 'and'}, {'translatedText': 'y', 'input': 'and'}, {'translatedText': 'en', 'input': 'at'}, {'translatedText': 'en', 'input': 'at'}, {'translatedText': 'Rey de la hamburguesa', 'input': 'Burger King'}, {'translatedText': 'Rey de la hamburguesa', 'input': 'Burger King'}, {'translatedText': 'Chick-fil-A', 'input': 'Chick-fil-A'}, {'translatedText': 'Chick-fil-ay', 'input': 'Chick-fil-Ay'}, {'translatedText': 'McDonald&#39;s', 'input': "McDonald's"}, {'translatedText': 'McDonald&#39;s', 'input': "McDonald's"}, {'translatedText': 'Pizza Hut', 'input': 'Pizza Hut'}, {'translatedText': 'Pizza Hut', 'input': 'Pizza Hut'}, {'translatedText': 'Taco Bell', 'input': 'Taco Bell'}, {'translatedText': 'Taco Bell', 'input': 'Taco Bell'}, {'translatedText': 'De Wendy', 'input': "Wendy's"}, {'translatedText': 'De Wendy', 'input': "Wendy's"}, {'translatedText': '-s', 'input': '-s'}, {'translatedText': '.', 'input': '.'}, {'translatedText': '.', 'input': '.'}, {'translatedText': 'Chino', 'input': 'Chinese'}, {'translatedText': 'Restaurante chino', 'input': 'Chinese restaurant'}, {'translatedText': 'GENTE', 'input': 'PEOPLE'}, {'translatedText': 'PREGUNTAS', 'input': 'QUESTIONS'}, {'translatedText': 'cualquier', 'input': 'any'}, {'translatedText': 'cuerpo', 'input': 'body'}, {'translatedText': 'cuerpo', 'input': 'body'}, {'translatedText': 'día', 'input': 'day'}, {'translatedText': 'día', 'input': 'day'}, {'translatedText': 'cómo', 'input': 'how'}, {'translatedText': 'cómo', 'input': 'how'}, {'translatedText': 'más', 'input': 'more'}, {'translatedText': 'más', 'input': 'more'}, {'translatedText': 'uno', 'input': 'one'}, {'translatedText': 'uno', 'input': 'one'}, {'translatedText': 'lugar', 'input': 'place'}, {'translatedText': 'lugar', 'input': 'place'}, {'translatedText': 'cosa', 'input': 'thing'}]

    # translations = {}
    # for text in texts:
    #     # result = translate_client.translate(text, source_language=sourceLang, target_language=targetLang)
    #     translations[text] = result['translatedText']
    
    translations["target_lang"] = targetLanguage

    translated_file = processor.create_translated_file(gridset_file, translations)

    return FileResponse(translated_file, media_type="application/octet-stream")