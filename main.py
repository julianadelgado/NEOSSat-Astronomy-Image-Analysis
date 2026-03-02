from pathlib import Path
import cv2

from fastapi import FastAPI
from astropy.io import fits

from pretraitements.core.PreprocessRequest import PreprocessRequest
from pretraitements.metrics import Metrics
from pretraitements.pipeline import Pipeline
from pretraitements.preprocessors.fits_to_png import FitsToPng
from pretraitements.preprocessors.star_detection import StarDetection
from detectors.dl_streak_detector import DLStreakDetector

app = FastAPI()

metrics = Metrics()

pipeline = Pipeline(
    preprocessors=[StarDetection(), FitsToPng()],
    metrics=metrics,
)

dl_streak_detector = DLStreakDetector()


@app.post("/pretraitements")
def run_preprocessing(req: PreprocessRequest):
    results = pipeline.run(
        fits_path=Path(req.fits_file),
        selected=req.preprocessors,
        output_dir=Path("results"),
    )
    return {"status": "ok", "results": results}


@app.post("/streak-detection")
def run_streak_detection(req: PreprocessRequest = None):

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
    """Liste tous les pré-traitements disponibles"""
    return {"available_preprocessors": list(pipeline.preprocessors.keys())}
