import time
from pathlib import Path
from typing import Dict, List

from astropy.io import fits

from pretraitements.core.IPreprocessor import IPreprocessor
from pretraitements.metrics import Metrics


class Pipeline:

    def __init__(self, preprocessors: List[IPreprocessor], metrics: Metrics):
        self.preprocessors = {p.name(): p for p in preprocessors}
        self.metrics = metrics

    def run(
        self,
        fits_path: Path,
        selected: List[str],
        output_dir: Path,
    ) -> Dict:
        image = fits.getdata(fits_path)
        header = fits.getheader(fits_path)

        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        for name in selected:
            preprocessor = self.preprocessors.get(name)
            if not preprocessor:
                raise ValueError(f"Pré-traitement inconnu: {name}")

            start = time.perf_counter()
            metadata = preprocessor.run(image, header, output_dir)
            duration = time.perf_counter() - start

            self.metrics.register(duration)
            results[name] = metadata

        return results
