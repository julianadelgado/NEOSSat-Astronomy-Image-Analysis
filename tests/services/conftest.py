import pytest
from unittest.mock import MagicMock
from services.email_service import EmailService


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