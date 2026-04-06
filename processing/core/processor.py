from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class IProcessor(ABC):
    @abstractmethod
    def name(self) -> str:
        """Unique name of the processor"""
        pass

    @abstractmethod
    def run(self, image: np.ndarray, header, output_dir: Path, **kwargs) -> dict:
        """
        Runs the processor.
        Returns a dictionary of result metadata (e.g. number of stars detected).
        """
        pass
