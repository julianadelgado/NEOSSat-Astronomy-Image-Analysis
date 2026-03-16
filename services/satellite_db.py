import datetime
from typing import Any, Dict, List, Optional


class SatelliteDatabaseService:
    """
    Service for querying a satellite database using Skyfield and Celestrak.
    Downloads Active satellite TLEs, propagates orbits, and correlates
    streak RA/Dec to nearby satellites.
    """

    def __init__(self):
        try:
            from skyfield.api import load

            self.load = load
            self.ts = load.timescale()
            self.celestrak_url = (
                "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
            )
            self.satellites = None
        except ImportError:
            print(
                "Error: 'skyfield' package is not installed. Satellite correlation will not work."
            )
            print("Please install it with: pip install skyfield")
            self.satellites = []

    def _load_satellites(self):
        if self.satellites is None:
            print("[SatelliteDatabaseService] Loading satellite TLEs from Celestrak...")
            try:
                # Load TLE data directly from Celestrak
                self.satellites = self.load.tle_file(self.celestrak_url, reload=False)
                print(
                    f"[SatelliteDatabaseService] Loaded {len(self.satellites)} satellites."
                )
            except Exception as e:
                print(f"[SatelliteDatabaseService] Failed to load satellites: {e}")
                self.satellites = []

    def query_satellites_at_position(
        self,
        ra_deg: float,
        dec_deg: float,
        observation_time: datetime.datetime,
        search_radius_arcmin: float = 10.0,
    ) -> List[Dict[str, Any]]:
        self._load_satellites()

        if not self.satellites:
            return []

        from datetime import timezone

        import astropy.units as u
        from astropy.coordinates import SkyCoord

        # Ensure observation time is time-zone aware (assuming UTC from FITS if absent)
        if observation_time.tzinfo is None:
            observation_time = observation_time.replace(tzinfo=timezone.utc)

        t = self.ts.from_datetime(observation_time)
        target_coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg)
        search_radius = search_radius_arcmin * u.arcmin

        print(
            f"[SatelliteDatabaseService] Querying {len(self.satellites)} satellites near RA={ra_deg:.4f}, "
            f"Dec={dec_deg:.4f} at {observation_time} (radius={search_radius_arcmin}') ... "
        )

        results = []

        # Vectorized or fast iteration setup
        # For full accuracy, observer should be NEOSSat orbit.
        # As a fallback, we compute geocentric positions of satellites.
        for sat in self.satellites:
            try:
                # Get the geocentric position.
                # (For true precision, replace with NEOSSat's topocentric/orbit location if known)
                geometry = sat.at(t)
                sat_ra, sat_dec, distance = geometry.radec()

                sat_coord = SkyCoord(
                    ra=sat_ra.degrees * u.deg, dec=sat_dec.degrees * u.deg
                )
                sep = target_coord.separation(sat_coord)

                if sep <= search_radius:
                    results.append(
                        {
                            "name": sat.name,
                            "catalog_id": str(sat.model.satnum),
                            "ra_deg": float(sat_ra.degrees),
                            "dec_deg": float(sat_dec.degrees),
                            "distance_km": float(distance.km),
                            "separation_arcmin": float(sep.arcmin),
                            "confidence": max(
                                0.0, 1.0 - (sep.arcmin / search_radius_arcmin)
                            ),
                            "notes": "Matched via Skyfield and Celestrak TLEs (Geocentric)",
                        }
                    )
            except Exception as _:
                # In case propagation fails for an old TLE
                continue

        # Sort by closest match
        results.sort(key=lambda x: x["separation_arcmin"])
        return results

    def correlate_streak_with_satellite(
        self,
        streak_ra: float,
        streak_dec: float,
        observation_time: datetime.datetime,
        search_radius_arcmin: float = 10.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best matching satellite for a detected streak.

        Args:
            streak_ra: Streak center RA in degrees
            streak_dec: Streak center Dec in degrees
            observation_time: Time of observation
            search_radius_arcmin: Search radius in arcminutes

        Returns:
            Best matching satellite dictionary or None if no match found
        """
        satellites = self.query_satellites_at_position(
            streak_ra, streak_dec, observation_time, search_radius_arcmin
        )

        if not satellites:
            return None

        # Return the satellite with the highest confidence
        best_match = max(satellites, key=lambda x: x.get("confidence", 0))
        return best_match
