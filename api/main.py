from pathlib import Path

import uvicorn
from astropy.io import fits
from fastapi import FastAPI, HTTPException

from api.preprocess_request import PreprocessRequest
from handlers.data_manager import DataManager
from preprocessing.metrics import Metrics
from preprocessing.pipeline import Pipeline
from preprocessing.preprocessors.fits_to_png import FitsToPng
from tasks.stacking.image_stacking import ImageStacking
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
            raise HTTPException(
                status_code=404,
                detail=f"File {req.fits_file} not found in current directory or project root."
            )
    else:
        fits_path = req_path

    results = {}

    # Run standard preprocessing pipeline if preprocessors are specified
    if req.preprocessors:
        pipeline_results = pipeline.run(
            fits_path=fits_path,
            selected=req.preprocessors,
            output_dir=Path("results"),
        )
        results["pipeline"] = pipeline_results

    # Run streak detection if requested
    if req.run_streak_detection:
        streak_detector = dl_streak_detector.DLStreakDetector(
            conf_thres=req.streak_detection_conf_threshold,
            iou_thres=req.streak_detection_iou_threshold,
            data_dir=str(fits_path.parent),
        )
        streak_results = streak_detector.run()
        results["streak_detection"] = streak_results

    # Run star detection if requested
    if req.run_star_detection:
        try:
            with fits.open(fits_path) as hdul:
                image_data = hdul[0].data
                header = hdul[0].header
                
                star_detector = StarDetection()
                star_results = star_detector.run(
                    image=image_data,
                    header=header,
                    output_dir=Path("results") / "star_detection"
                )
                results["star_detection"] = star_results
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Star detection failed: {str(e)}"
            )

    # Run image stacking if requested
    if req.run_image_stacking:
        if not req.images_path:
            raise HTTPException(
                status_code=400,
                detail="images_path is required for image stacking"
            )
        if not req.date_obs:
            raise HTTPException(
                status_code=400,
                detail="date_obs is required for image stacking"
            )
        
        try:
            data_manager = DataManager(file_path=str(fits_path))
            stacker = ImageStacking(
                images_path=req.images_path,
                data_manager=data_manager,
                date_obs=req.date_obs
            )
            stacker.stack_images()
            results["image_stacking"] = {
                "status": "completed",
                "date_obs": req.date_obs,
                "images_path": req.images_path
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Image stacking failed: {str(e)}"
            )

    # If nothing was requested, return an error
    if not results:
        raise HTTPException(
            status_code=400,
            detail="No processing requested. Please specify at least one of: preprocessors, run_streak_detection, run_star_detection, or run_image_stacking"
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
