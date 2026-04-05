from pathlib import Path

import numpy as np

from handlers.data_manager import DataManager
from preprocessing.core.preprocessor import IPreprocessor
from tasks.stacking.image_stacking import ImageStacking


class ImageStackingPreprocessor(IPreprocessor):
    def name(self) -> str:
        return "image_stacking"

    def run(self, image: np.ndarray, header, output_dir: Path, **kwargs) -> dict:
        fits_path = kwargs.get("fits_path")
        images_path = kwargs.get("images_path")
        date_obs = kwargs.get("date_obs")

        if not fits_path:
            raise ValueError("fits_path is required for image stacking")
        if not images_path:
            raise ValueError("images_path is required for image stacking")
        if not date_obs:
            raise ValueError("date_obs is required for image stacking")

        data_manager = DataManager(file_path=str(fits_path))
        stacker = ImageStacking(
            images_path=images_path,
            data_manager=data_manager,
            date_obs=date_obs,
        )
        stacker.stack_images()

        return {
            "status": "completed",
            "date_obs": date_obs,
            "images_path": images_path,
        }
