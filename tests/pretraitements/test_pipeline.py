from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pretraitements.metrics import Metrics
from pretraitements.pipeline import Pipeline


def test_pipeline_runs_selected_preprocessor(tmp_path):
    fake_image = np.zeros((10, 10))
    fake_header = {"SIMPLE": True}

    mock_preprocessor = MagicMock()
    mock_preprocessor.name.return_value = "mock_proc"
    mock_preprocessor.run.return_value = {"ok": True}

    metrics = Metrics()
    pipeline = Pipeline([mock_preprocessor], metrics)

    getdata_path = "pretraitements.pipeline.fits.getdata"
    getheader_path = "pretraitements.pipeline.fits.getheader"

    with (
        patch(getdata_path, return_value=fake_image),
        patch(getheader_path, return_value=fake_header),
    ):
        results = pipeline.run(
            fits_path=Path("fake.fits"),
            selected=["mock_proc"],
            output_dir=tmp_path,
        )

    mock_preprocessor.run.assert_called_once()
    assert results == {"mock_proc": {"ok": True}}
    assert metrics.count == 1


def test_pipeline_raises_for_unknown_preprocessor(tmp_path):
    pipeline = Pipeline([], Metrics())

    with pytest.raises(ValueError, match="Pré-traitement inconnu"):
        pipeline.run(
            fits_path=Path("fake.fits"),
            selected=["does_not_exist"],
            output_dir=tmp_path,
        )
