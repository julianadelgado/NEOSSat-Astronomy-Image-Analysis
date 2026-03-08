from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class IPreprocessor(ABC):
    @abstractmethod
    def name(self) -> str:
        """Unique name of the preprocessor"""
        pass

    @abstractmethod
    def run(self, image: np.ndarray, header, output_dir: Path) -> dict:
        """
        Runs the preprocessor.
        Returns a dictionary of result metadata (e.g. number of stars detected).
        """
        pass
