from pathlib import Path

import numpy as np

from processing.processors.fits_to_png import FitsToPng


def test_fits_to_png_creates_png(tmp_path):
    image = np.array([[0, 1], [2, 3]], dtype=float)
    header = {}

    processor = FitsToPng()
    result = processor.run(image, header, tmp_path)

    png_path = Path(result["png_saved"])

    assert png_path.exists()
    assert png_path.suffix == ".png"
