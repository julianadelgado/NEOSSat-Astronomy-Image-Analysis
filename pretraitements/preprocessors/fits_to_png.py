from pathlib import Path

import matplotlib  # pyright: ignore[reportMissingModuleSource]
import numpy as np  # pyright: ignore[reportMissingImports]

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # pyright: ignore[reportMissingModuleSource]
from astropy.io import fits  # pyright: ignore[reportMissingImports]

from pretraitements.core.IPreprocessor import IPreprocessor


class FitsToPngPreprocessor(IPreprocessor):
    """Convertit un fichier FITS en PNG normalisé (0-1) pour visualisation."""

    def name(self) -> str:
        return "fits_to_png"

    def run(self, image: np.ndarray, header, output_dir: Path) -> dict:
        """
        Comme ce pré-traitement ne dépend pas directement du tableau,
        on l'utilise pour générer un PNG de l'image FITS d'origine.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        png_path = output_dir / "image_normalisee.png"

        img_data = image.astype(float)
        img_data -= np.min(img_data)
        max_val = np.max(img_data)
        if max_val != 0:
            img_data /= max_val

        plt.imsave(str(png_path), img_data, cmap="gray")

        return {"png_saved": str(png_path)}
