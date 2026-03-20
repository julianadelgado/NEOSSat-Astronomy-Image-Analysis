from pathlib import Path

import numpy as np

from preprocessing.core.preprocessor import IPreprocessor


class FitsToPng(IPreprocessor):
    """Converts a FITS file to a normalized (0-1) PNG for visualization."""

    def name(self) -> str:
        return "fits_to_png"

    def run(
        self,
        image: np.ndarray,
        header,
        output_dir: Path,
        filename: str = "image_normalisee.png",
    ) -> dict:
        """
        Generates a normalized PNG from the original FITS image data.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        png_path = output_dir / filename

        img_data = image.astype(float)
        img_data -= np.min(img_data)
        max_val = np.max(img_data)
        if max_val != 0:
            img_data /= max_val

        # Configure matplotlib backend and import pyplot locally to avoid
        # module-level side-effects that trigger flake8 E402.
        import matplotlib as _matplotlib

        _matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.imsave(str(png_path), img_data, cmap="gray")

        return {"png_saved": str(png_path)}
