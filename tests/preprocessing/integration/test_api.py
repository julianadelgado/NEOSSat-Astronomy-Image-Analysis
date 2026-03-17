from unittest.mock import patch

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
    assert "available_preprocessors" in response.json()


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
    assert "star_detection" in data["results"]
    assert data["results"]["star_detection"]["stars_detected"] == 3

    mock_pipeline.run.assert_called_once_with(
        fits_path=fits_file,
        selected=["star_detection"],
        output_dir=mock_pipeline.run.call_args.kwargs["output_dir"],
    )
