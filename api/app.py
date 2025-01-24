import sys
import os

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, File, UploadFile
from aac_processors import GridsetProcessor  # Add this import

app = FastAPI()

@app.post("/upload/")
async def create_upload_file(file: UploadFile):
    processor = GridsetProcessor()

    demo_dir = "../examples/demofiles"
    gridset_file = os.path.join(demo_dir, "SimpleTest.gridset")

    texts = processor.extract_texts(gridset_file)

    translations = {}
    for i, text in enumerate(texts):
        translations[text] = f"Translated_{i}"
    translations["target_lang"] = "es"
    print(f"Created translations: {translations}")

    outputPath = os.path.join(demo_dir, "output.gridset")

    translated_file = processor.process_texts(
        gridset_file,
        translations,
        outputPath
    )

    return {
        "filename": file.filename,
        "textCount": len(texts),
        "outputPath": outputPath
    }