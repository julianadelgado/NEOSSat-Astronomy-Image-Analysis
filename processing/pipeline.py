import time
from pathlib import Path
from typing import Dict, List

from astropy.io import fits

from processing.core.processor import IProcessor
from processing.metrics import Metrics


class Pipeline:

    def __init__(self, processors: List[IProcessor], metrics: Metrics):
        self.processors = {p.name(): p for p in processors}
        self.metrics = metrics

    def run(
        self,
        fits_path: Path,
        selected: List[str],
        output_dir: Path,
        **kwargs,
    ) -> Dict:

        for name in selected:
            if name not in self.processors:
                raise ValueError(f"Pré-traitement inconnu: {name}")

        image = fits.getdata(fits_path)
        header = fits.getheader(fits_path)
        processor_kwargs = {"fits_path": fits_path, **kwargs}

        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        for name in selected:
            processor = self.processors[name]

            start = time.perf_counter()
            metadata = processor.run(image, header, output_dir, **processor_kwargs)
            duration = time.perf_counter() - start

            self.metrics.register(duration)
            results[name] = metadata

        return results
