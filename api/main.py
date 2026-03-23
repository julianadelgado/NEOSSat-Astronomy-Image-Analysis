from pathlib import Path

import uvicorn
from fastapi import FastAPI

from api.preprocess_request import PreprocessRequest
from preprocessing.metrics import Metrics
from preprocessing.pipeline import Pipeline
from preprocessing.preprocessors.fits_to_png import FitsToPng
from tasks.stars.star_detection import StarDetection
from tasks.stars.star_detection_legacy import StarDetectionLegacy
from tasks.streaks import dl_streak_detector

app = FastAPI()

metrics = Metrics()

pipeline = Pipeline(
    preprocessors=[StarDetection(), StarDetectionLegacy(), FitsToPng()],
    metrics=metrics,
)

dl_streak_detector = dl_streak_detector.DLStreakDetector()


@app.post("/preprocessing")
def run_preprocessing(req: PreprocessRequest):
    req_path = Path(req.fits_file)

    if not req_path.exists():
        project_root = Path(__file__).resolve().parents[1]
        candidate = project_root / req_path
        if candidate.exists():
            fits_path = candidate
        else:
            raise FileNotFoundError(
                f"File {req.fits_file} not found in current directory or project root."
            )
    else:
        fits_path = req_path

    results = pipeline.run(
        fits_path=fits_path,
        selected=req.preprocessors,
        output_dir=Path("results"),
    )
    return {"status": "ok", "results": results}


@app.post("/streak-detection")
def run_streak_detection():

    results = dl_streak_detector.run()

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
