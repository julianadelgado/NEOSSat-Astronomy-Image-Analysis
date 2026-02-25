from pathlib import Path

from fastapi import FastAPI  # pyright: ignore[reportMissingImports]

from pretraitements.core.PreprocessRequest import PreprocessRequest
from pretraitements.metrics import Metrics
from pretraitements.pipeline import Pipeline
from pretraitements.preprocessors.fits_to_png import FitsToPngPreprocessor
from pretraitements.preprocessors.star_detection import StarDetectionPreprocessor

app = FastAPI()

metrics = Metrics()

pipeline = Pipeline(
    preprocessors=[StarDetectionPreprocessor(), FitsToPngPreprocessor()],
    metrics=metrics,
)


@app.post("/pretraitements")
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
    """Liste tous les pré-traitements disponibles"""
    return {"available_preprocessors": list(pipeline.preprocessors.keys())}
