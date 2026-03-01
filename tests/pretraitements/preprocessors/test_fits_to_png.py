from pathlib import Path

import numpy as np

from pretraitements.preprocessors.fits_to_png import FitsToPng


def test_fits_to_png_creates_png(tmp_path):
    image = np.array([[0, 1], [2, 3]], dtype=float)
    header = {}

    preprocessor = FitsToPng()
    result = preprocessor.run(image, header, tmp_path)

    png_path = Path(result["png_saved"])

    assert png_path.exists()
    assert png_path.suffix == ".png"
