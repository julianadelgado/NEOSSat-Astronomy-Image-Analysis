from unittest.mock import MagicMock

import pytest

from services.email_service import EmailService
from services.report_service import ReportData, ReportSection, ReportService


@pytest.fixture
def email_service(monkeypatch):
    monkeypatch.setenv("SMTP_SERVER", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_USER", "sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "password")
    return EmailService()


@pytest.fixture
def make_fake_satellite():
    """Factory fixture that builds a mock satellite like a skyfield EarthSatellite."""

    def _factory(name, catalog_id, ra_deg, dec_deg, distance_km):
        radec_result = (
            MagicMock(degrees=ra_deg),
            MagicMock(degrees=dec_deg),
            MagicMock(km=distance_km),
        )
        geometry = MagicMock()
        geometry.radec.return_value = radec_result

        sat = MagicMock()
        sat.name = name
        sat.model.satnum = catalog_id
        sat.at.return_value = geometry
        return sat

    return _factory


@pytest.fixture
def report_service(tmp_path):
    return ReportService(reports_dir=tmp_path)


@pytest.fixture
def sample_image(tmp_path):
    image = tmp_path / "test_image.png"
    image.write_bytes(b"")
    return image


@pytest.fixture
def report_data_with_image(sample_image):
    return ReportData(
        task_name="Test Task",
        sections=[ReportSection(title="Results", images=[sample_image])],
    )
