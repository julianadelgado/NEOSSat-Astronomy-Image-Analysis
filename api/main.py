from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException

from api.preprocess_request import PreprocessRequest
from preprocessing.metrics import Metrics
from preprocessing.pipeline import Pipeline
from preprocessing.preprocessors.fits_to_png import FitsToPng
from preprocessing.preprocessors.image_stacking import ImageStackingPreprocessor
from preprocessing.preprocessors.streak_detection import StreakDetectionPreprocessor
from tasks.stars.star_detection import StarDetection
from tasks.stars.star_detection_legacy import StarDetectionLegacy
from tasks.streaks import dl_streak_detector

app = FastAPI()

metrics = Metrics()

pipeline = Pipeline(
    preprocessors=[
        StarDetection(),
        StarDetectionLegacy(),
        FitsToPng(),
        StreakDetectionPreprocessor(),
        ImageStackingPreprocessor(),
    ],
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
            raise HTTPException(
                status_code=404,
                detail=f"File {req.fits_file} not found in current directory or project root.",
            )
    else:
        fits_path = req_path

    selected = list(req.preprocessors or [])

    if req.run_star_detection:
        selected.append("star_detection")
    if req.run_streak_detection:
        selected.append("streak_detection")
    if req.run_image_stacking:
        selected.append("image_stacking")

    if req.run_image_stacking and not req.images_path:
        raise HTTPException(
            status_code=400, detail="images_path is required for image stacking"
        )
    if req.run_image_stacking and not req.date_obs:
        raise HTTPException(
            status_code=400, detail="date_obs is required for image stacking"
        )

    # Keep user order while removing duplicate preprocessors.
    selected = list(dict.fromkeys(selected))

    # If nothing was requested, return an error
    if not selected:
        raise HTTPException(
            status_code=400,
            detail="No processing requested. Please specify at least one of: preprocessors, run_streak_detection, run_star_detection, or run_image_stacking",
        )

    try:
        pipeline_results = pipeline.run(
            fits_path=fits_path,
            selected=selected,
            output_dir=Path("results"),
            streak_detection_conf_threshold=req.streak_detection_conf_threshold,
            streak_detection_iou_threshold=req.streak_detection_iou_threshold,
            images_path=req.images_path,
            date_obs=req.date_obs,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    results = {"pipeline": pipeline_results}

    if req.run_star_detection and "star_detection" in pipeline_results:
        results["star_detection"] = pipeline_results["star_detection"]
    if req.run_streak_detection and "streak_detection" in pipeline_results:
        results["streak_detection"] = pipeline_results["streak_detection"]
    if req.run_image_stacking and "image_stacking" in pipeline_results:
        results["image_stacking"] = pipeline_results["image_stacking"]

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
