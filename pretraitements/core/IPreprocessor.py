from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np  # pyright: ignore[reportMissingImports]


class IPreprocessor(ABC):
    @abstractmethod
    def name(self) -> str:
        """Nom unique du pré-traitement"""
        pass

    @abstractmethod
    def run(self, image: np.ndarray, header, output_dir: Path) -> dict:
        """
        Exécute le pré-traitement.
        Retourne un dictionnaire de données (ex: nombre d'étoiles détectées).
        """
        pass
