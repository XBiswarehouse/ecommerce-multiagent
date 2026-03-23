"""FastAPI主应用"""
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from routers.workflow import run_analysis
from models.database import init_db

app = FastAPI(title="电商多智能体分析系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class AnalysisRequest(BaseModel):
    data_size: Optional[int] = 500


@app.get("/")
async def root():
    return {"message": "电商多智能体分析系统", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    result = run_analysis(data_size=request.data_size)
    return result


@app.post("/analyze/upload")
async def analyze_upload(file: UploadFile = File(...)):
    result = run_analysis(uploaded_file=file.file)
    return result