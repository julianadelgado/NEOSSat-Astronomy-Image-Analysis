from pathlib import Path

import numpy as np

from processing.core.processor import IProcessor
from tasks.streaks import dl_streak_detector


class StreakDetectionProcessor(IProcessor):
    def name(self) -> str:
        return "streak_detection"

    def run(self, image: np.ndarray, header, output_dir: Path, **kwargs) -> dict:
        fits_path = kwargs.get("fits_path")
        if not fits_path:
            raise ValueError("fits_path is required for streak detection")

        detector = dl_streak_detector.DLStreakDetector(
            conf_thres=kwargs.get("streak_detection_conf_threshold", 0.25),
            iou_thres=kwargs.get("streak_detection_iou_threshold", 0.45),
            data_dir=str(Path(fits_path).parent),
        )

        return detector.run()
