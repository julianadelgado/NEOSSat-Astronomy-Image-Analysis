from pathlib import Path

import numpy as np

from processing.core.processor import IProcessor


class FitsToPng(IProcessor):
    """Converts a FITS file to a normalized (0-1) PNG for visualization."""

    def name(self) -> str:
        return "fits_to_png"

    def run(
        self,
        image: np.ndarray,
        header,
        output_dir: Path,
        filename: str = "source_image.png",
        **kwargs,
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

        import matplotlib as _matplotlib  # noqa: E402

        _matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.imshow(img_data, cmap="gray", origin="lower")
        plt.axis("off")
        plt.savefig(png_path, dpi=300, bbox_inches="tight", pad_inches=0)
        plt.close()

        return {"png_saved": str(png_path)}
