from pathlib import Path

import uvicorn
from fastapi import FastAPI

from preprocessing.core.preprocess_request import PreprocessRequest
from preprocessing.metrics import Metrics
from preprocessing.pipeline import Pipeline
from preprocessing.preprocessors.fits_to_png import FitsToPng
from preprocessing.preprocessors.star_detection import StarDetection

app = FastAPI()

metrics = Metrics()

pipeline = Pipeline(
    preprocessors=[StarDetection(), FitsToPng()],
    metrics=metrics,
)


@app.post("/preprocessing")
def run_preprocessing(req: PreprocessRequest):
    results = pipeline.run(
        fits_path=Path(req.fits_file),
        selected=req.preprocessors,
        output_dir=Path("results"),
    )
    return {"status": "ok", "results": results}


@app.get("/health")
def health():
    return {
        "status": "running",
        "average_preprocessing_time_sec": metrics.average_time(),
    }


@app.get("/catalog")
def catalog():
    """List all available preprocessors"""
    return {"available_preprocessors": list(pipeline.preprocessors.keys())}


def start():
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
