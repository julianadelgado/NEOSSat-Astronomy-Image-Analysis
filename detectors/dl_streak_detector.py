import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add dl_streak_detect to sys.path to ensure relative imports inside the package work as expected
# and legacy torch weights can be loaded (models expects models module at root level)
sys.path.append(str(Path(__file__).parent.parent / "dl_streak_detect"))
from dl_streak_detect.detect import detect
from pretraitements.preprocessors.fits_to_png import FitsToPng

from .core.IDetector import IDetector

DATA_DIR = Path("data")
INFERENCE_DATA_DIR = Path("inference_data")
RESULT_DATA_DIR = Path("result_data")


class DLStreakDetector(IDetector):
    def __init__(
        self,
        weights_path: str = None,
        img_size: int = 640,
        conf_thres: float = 0.25,
        iou_thres: float = 0.45,
    ):
        base_path = Path(__file__).parent.parent / "dl_streak_detect"
        self.weights_path = weights_path or str(base_path / "weights/best.pt")
        self.img_size = img_size
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres

    def name(self) -> str:
        return "DL Streak Detector"

    def required_preprocessors(self) -> List[str]:
        return ["fits_to_png"]

    def run(self) -> Dict[str, Any]:
        """
        Run the DL Streak Detector.
        Checks the data folder, runs preprocessors, outputs into inference_data,
        then runs inference and outputs results to result_data.
        """
        # Ensure directories exist
        INFERENCE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_DATA_DIR.mkdir(parents=True, exist_ok=True)

        results_summary = []

        if not DATA_DIR.exists():
            msg = f"Data directory '{DATA_DIR.absolute()}' does not exist."
            print(msg)
            return {"error": msg, "streaks": []}

        files = list(DATA_DIR.glob("*"))
        if not files:
            msg = f"No files found in '{DATA_DIR.absolute()}'."
            print(msg)
            return {"error": msg, "streaks": []}

        # Initialize preprocessor
        fits_to_png = FitsToPng()

        for file_path in files:
            try:
                if file_path.suffix.lower() in [".fits", ".fit"]:
                    from astropy.io import fits

                    with fits.open(file_path) as hdul:
                        data = hdul[0].data
                        header = hdul[0].header
                        if data is None:
                            continue

                        # Use FitsToPng preprocessor
                        fits_to_png.run(
                            data,
                            header,
                            INFERENCE_DATA_DIR,
                            filename=f"{file_path.stem}.png",
                        )
                elif file_path.suffix.lower() in [".jpg", ".png", ".jpeg"]:
                    import shutil

                    png_path = INFERENCE_DATA_DIR / file_path.name
                    shutil.copy(file_path, png_path)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

        # Run inference on the inference_data folder
        opt = argparse.Namespace(
            weights=[self.weights_path],
            source=str(INFERENCE_DATA_DIR),  # Run on the whole folder
            img_size=self.img_size,
            conf_thres=self.conf_thres,
            iou_thres=self.iou_thres,
            device="",
            view_img=False,
            save_txt=True,
            save_conf=True,
            nosave=False,  # Maybe allow saving? User said "results outputed to a folder named result_data"
            classes=None,
            agnostic_nms=False,
            augment=False,
            update=False,
            project=str(RESULT_DATA_DIR),
            name="inference",
            exist_ok=True,
            no_trace=False,
        )

        try:
            detect(opt=opt)

            # Parse results from the text files generated
            labels_dir = Path(opt.project) / opt.name / "labels"
            if labels_dir.exists():
                for label_file in labels_dir.glob("*.txt"):
                    with open(label_file, "r") as f:
                        file_results = []
                        for line in f.readlines():
                            parts = line.strip().split()
                            if len(parts) >= 6:
                                file_results.append(
                                    {
                                        "class": str(int(parts[0])),
                                        "confidence": float(parts[5]),
                                        "box": [float(x) for x in parts[1:5]],
                                    }
                                )
                        results_summary.append(
                            {"file": label_file.stem, "detections": file_results}
                        )
            else:
                print(f"No label directory found at {labels_dir}. No detections made.")
                # Not necessarily an error, just no detections, but return empty summary is fine.

        except Exception as e:
            msg = f"Inference failed: {str(e)}"
            print(msg)
            return {"error": msg, "streaks": results_summary}

        return {"streaks": results_summary}
