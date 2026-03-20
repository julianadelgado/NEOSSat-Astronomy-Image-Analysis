from abc import ABC, abstractmethod
from typing import Any, Dict, List

import numpy as np


class IDetector(ABC):
    @abstractmethod
    def name(self) -> str:
        """Name of the detector"""
        pass

    @abstractmethod
    def required_preprocessors(self) -> List[str]:
        """
        List of preprocessor names required by this detector.
        These preprocessors must be run before the detector executes.
        """
        pass

    @abstractmethod
    def run(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Run the detector on the image.
        Returns a dictionary of detection results.
        """
        pass
