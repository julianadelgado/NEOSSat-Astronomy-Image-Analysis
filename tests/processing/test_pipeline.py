from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from processing.metrics import Metrics
from processing.pipeline import Pipeline


def test_pipeline_runs_selected_processor(tmp_path):
    fake_image = np.zeros((10, 10))
    fake_header = {"SIMPLE": True}

    mock_processor = MagicMock()
    mock_processor.name.return_value = "mock_proc"
    mock_processor.run.return_value = {"ok": True}

    metrics = Metrics()
    pipeline = Pipeline([mock_processor], metrics)

    getdata_path = "processing.pipeline.fits.getdata"
    getheader_path = "processing.pipeline.fits.getheader"

    with (
        patch(getdata_path, return_value=fake_image),
        patch(getheader_path, return_value=fake_header),
    ):
        results = pipeline.run(
            fits_path=Path("fake.fits"),
            selected=["mock_proc"],
            output_dir=tmp_path,
        )

    mock_processor.run.assert_called_once()
    assert results == {"mock_proc": {"ok": True}}
    assert metrics.count == 1


def test_pipeline_raises_for_unknown_processor(tmp_path):
    pipeline = Pipeline([], Metrics())

    with pytest.raises(ValueError, match="Pré-traitement inconnu"):
        pipeline.run(
            fits_path=Path("fake.fits"),
            selected=["does_not_exist"],
            output_dir=tmp_path,
        )
