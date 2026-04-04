from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from astropy.io import fits
from fastapi.testclient import TestClient


def test_health_endpoint():
    from api import main

    client = TestClient(main.app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "running"
    assert "average_preprocessing_time_sec" in payload


def test_catalog_endpoint():
    from api import main

    client = TestClient(main.app)
    response = client.get("/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert "available_preprocessors" in payload
    assert isinstance(payload["available_preprocessors"], list)


def test_preprocessing_returns_404_for_missing_file():
    from api import main

    client = TestClient(main.app)
    response = client.post(
        "/preprocessing",
        json={"fits_file": "does/not/exist.fits", "preprocessors": ["star_detection"]},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_preprocessing_requires_at_least_one_operation(tmp_path):
    from api import main

    client = TestClient(main.app)
    fits_file = tmp_path / "existing.fits"
    fits_file.write_bytes(b"")

    response = client.post(
        "/preprocessing",
        json={"fits_file": str(fits_file)},
    )

    assert response.status_code == 400
    assert "No processing requested" in response.json()["detail"]


def test_run_preprocessing_endpoint(tmp_path):
    from fastapi.testclient import TestClient

    from api import main

    client = TestClient(main.app)

    fits_file = tmp_path / "fake.fits"
    fits_file.write_bytes(b"")

    pipeline_path = "api.main.pipeline"

    with patch(pipeline_path) as mock_pipeline:
        mock_pipeline.run.return_value = {"star_detection": {"stars_detected": 5}}

        payload = {"fits_file": str(fits_file), "preprocessors": ["star_detection"]}
        response = client.post("/preprocessing", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "results" in data
    mock_pipeline.run.assert_called_once()


def test_run_preprocessing_star_detection(tmp_path):
    from api import main

    client = TestClient(main.app)

    fits_file = tmp_path / "fake_star.fits"
    fits_file.write_bytes(b"")

    pipeline_path = "api.main.pipeline"

    with patch(pipeline_path) as mock_pipeline:

        mock_pipeline.run.return_value = {"star_detection": {"stars_detected": 3}}

        payload = {
            "fits_file": str(fits_file),
            "preprocessors": ["star_detection"],
        }

        response = client.post("/preprocessing", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert "results" in data
    assert "pipeline" in data["results"]
    assert "star_detection" in data["results"]["pipeline"]
    assert data["results"]["pipeline"]["star_detection"]["stars_detected"] == 3

    mock_pipeline.run.assert_called_once_with(
        fits_path=fits_file,
        selected=["star_detection"],
        output_dir=mock_pipeline.run.call_args.kwargs["output_dir"],
    )


def test_preprocessing_pipeline_results_are_nested_under_pipeline(tmp_path):
    from api import main

    client = TestClient(main.app)
    fits_file = tmp_path / "fake_nested.fits"
    fits_file.write_bytes(b"")

    expected_pipeline = {"star_detection": {"stars_detected": 5}}
    mock_run = MagicMock(return_value=expected_pipeline)
    main.pipeline.run = mock_run

    response = client.post(
        "/preprocessing",
        json={"fits_file": str(fits_file), "preprocessors": ["star_detection"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["results"]["pipeline"] == expected_pipeline
    mock_run.assert_called_once()


def test_preprocessing_image_stacking_requires_images_path(tmp_path):
    from api import main

    client = TestClient(main.app)
    fits_file = tmp_path / "stack_a.fits"
    fits_file.write_bytes(b"")

    response = client.post(
        "/preprocessing",
        json={
            "fits_file": str(fits_file),
            "run_image_stacking": True,
            "date_obs": "2024-01-15",
        },
    )

    assert response.status_code == 400
    assert "images_path is required" in response.json()["detail"]


def test_preprocessing_image_stacking_requires_date_obs(tmp_path):
    from api import main

    client = TestClient(main.app)
    fits_file = tmp_path / "stack_b.fits"
    fits_file.write_bytes(b"")

    response = client.post(
        "/preprocessing",
        json={
            "fits_file": str(fits_file),
            "run_image_stacking": True,
            "images_path": "data/",
        },
    )

    assert response.status_code == 400
    assert "date_obs is required" in response.json()["detail"]


def test_streak_detection_endpoint_uses_global_detector(monkeypatch):
    from api import main

    client = TestClient(main.app)
    fake_detector = SimpleNamespace(run=MagicMock(return_value={"streaks": [{"id": 1}]}))
    monkeypatch.setattr(main, "dl_streak_detector", fake_detector)

    response = client.post("/streak-detection")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["results"] == {"streaks": [{"id": 1}]}
    fake_detector.run.assert_called_once()


def test_preprocessing_runs_star_streak_and_image_stacking_together(
    tmp_path, monkeypatch
):
    from api import main

    client = TestClient(main.app)

    # Create a valid FITS file so the endpoint can read image/header for star detection.
    fits_file = tmp_path / "all_ops.fits"
    fits.PrimaryHDU(np.zeros((16, 16), dtype=np.float32)).writeto(fits_file)

    fake_star_detector = SimpleNamespace(
        run=MagicMock(return_value={"stars_detected": 7})
    )
    fake_streak_runner = SimpleNamespace(run=MagicMock(return_value={"streaks": [{"id": 2}]}))
    fake_streak_module = SimpleNamespace(
        DLStreakDetector=MagicMock(return_value=fake_streak_runner)
    )
    fake_data_manager = MagicMock()
    fake_stacker = MagicMock()
    fake_stacker.stack_images = MagicMock()

    monkeypatch.setattr(main, "StarDetection", MagicMock(return_value=fake_star_detector))
    monkeypatch.setattr(main, "dl_streak_detector", fake_streak_module)
    monkeypatch.setattr(main, "DataManager", MagicMock(return_value=fake_data_manager))
    monkeypatch.setattr(main, "ImageStacking", MagicMock(return_value=fake_stacker))

    response = client.post(
        "/preprocessing",
        json={
            "fits_file": str(fits_file),
            "run_star_detection": True,
            "run_streak_detection": True,
            "run_image_stacking": True,
            "images_path": "data/",
            "date_obs": "2024-01-15",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["results"]["star_detection"] == {"stars_detected": 7}
    assert payload["results"]["streak_detection"] == {"streaks": [{"id": 2}]}
    assert payload["results"]["image_stacking"] == {
        "status": "completed",
        "date_obs": "2024-01-15",
        "images_path": "data/",
    }

    main.StarDetection.assert_called_once()
    fake_star_detector.run.assert_called_once()
    main.dl_streak_detector.DLStreakDetector.assert_called_once()
    fake_streak_runner.run.assert_called_once()
    main.DataManager.assert_called_once_with(file_path=str(fits_file))
    main.ImageStacking.assert_called_once_with(
        images_path="data/",
        data_manager=fake_data_manager,
        date_obs="2024-01-15",
    )
    fake_stacker.stack_images.assert_called_once()
