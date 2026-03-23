from unittest.mock import MagicMock, patch

from services.satellite_db_service import SatelliteDatabaseService
# from conftest import make_fake_satellite
import datetime

def test_query_returns_empty_when_no_match(make_fake_satellite):
    service = SatelliteDatabaseService.__new__(SatelliteDatabaseService)
    service.ts = MagicMock()
    service.satellites = [make_fake_satellite("ISS", 25544, 10.0, 20.0, 400.0)]

    obs_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
    results = service.query_satellites_at_position(30.0, 40.0, obs_time, search_radius_arcmin=10.0)

    assert results == []
    assert len(results) == 0

    

def test_query_returns_match_within_radius(make_fake_satellite):
    service = SatelliteDatabaseService.__new__(SatelliteDatabaseService)
    service.ts = MagicMock()
    service.satellites = [make_fake_satellite("ISS", 25544, 10.0, 20.0, 400.0)]

    obs_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
    results = service.query_satellites_at_position(10.0, 20.0, obs_time, search_radius_arcmin=10.0)

    assert len(results) == 1
    assert results[0]["name"] == "ISS"
    assert results[0]["catalog_id"] == "25544"
    assert 0.0 <= results[0]["confidence"] <= 1.0
