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
    

    return {"filename": file.filename}