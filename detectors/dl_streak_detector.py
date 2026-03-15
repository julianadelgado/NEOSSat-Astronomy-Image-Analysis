import argparse
import sys
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Add dl_streak_detect to sys.path to ensure relative imports inside the package work as expected
# and legacy torch weights can be loaded (models expects models module at root level)
sys.path.append(str(Path(__file__).parent.parent / "dl_streak_detect"))
from dl_streak_detect.detect import detect
from pretraitements.preprocessors.fits_to_png import FitsToPng

from .core.IDetector import IDetector

DATA_DIR = Path("data")
INFERENCE_DATA_DIR = Path("inference_data")
RESULT_DATA_DIR = Path("result_data")


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
            self.celestrak_url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle'
            self.satellites = None
        except ImportError:
            print("Error: 'skyfield' package is not installed. Satellite correlation will not work.")
            print("Please install it with: pip install skyfield")
            self.satellites = []

    def _load_satellites(self):
        if self.satellites is None:
            print("[SatelliteDatabaseService] Loading satellite TLEs from Celestrak...")
            try:
                # Load TLE data directly from Celestrak
                self.satellites = self.load.tle_file(self.celestrak_url, reload=False)
                print(f"[SatelliteDatabaseService] Loaded {len(self.satellites)} satellites.")
            except Exception as e:
                print(f"[SatelliteDatabaseService] Failed to load satellites: {e}")
                self.satellites = []

    def query_satellites_at_position(
        self,
        ra_deg: float,
        dec_deg: float,
        observation_time: datetime,
        search_radius_arcmin: float = 10.0,
    ) -> List[Dict[str, Any]]:
        self._load_satellites()
        
        if not self.satellites:
            return []

        from astropy.coordinates import SkyCoord
        import astropy.units as u
        from datetime import timezone

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

                sat_coord = SkyCoord(ra=sat_ra.degrees * u.deg, dec=sat_dec.degrees * u.deg)
                sep = target_coord.separation(sat_coord)

                if sep <= search_radius:
                    results.append({
                        "name": sat.name,
                        "catalog_id": str(sat.model.satnum),
                        "ra_deg": float(sat_ra.degrees),
                        "dec_deg": float(sat_dec.degrees),
                        "distance_km": float(distance.km),
                        "separation_arcmin": float(sep.arcmin),
                        "confidence": max(0.0, 1.0 - (sep.arcmin / search_radius_arcmin)),
                        "notes": "Matched via Skyfield and Celestrak TLEs (Geocentric)"
                    })
            except Exception as e:
                # In case propagation fails for an old TLE
                continue

        # Sort by closest match
        results.sort(key=lambda x: x["separation_arcmin"])
        return results

    def correlate_streak_with_satellite(
        self,
        streak_ra: float,
        streak_dec: float,
        observation_time: datetime,
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


# Utils

def extract_wcs_from_fits_header(header) -> Optional[Any]:
    """
    Extract WCS (World Coordinate System) object from FITS header.

    Args:
        header: FITS header object from astropy

    Returns:
        astropy.wcs.WCS object or None if WCS not available
    """
    try:
        from astropy.wcs import WCS

        wcs = WCS(header)
        if wcs.has_celestial:
            return wcs
        else:
            print("Warning: FITS header does not contain valid WCS information")
            return None
    except Exception as e:
        print(f"Error extracting WCS from header: {e}")
        return None


def pixel_bbox_to_world_coords(
    wcs: Any,
    x_pixel: float,
    y_pixel: float,
    width_pixel: float = None,
    height_pixel: float = None,
) -> Tuple[float, float, Optional[Tuple[float, float, float, float]]]:
    """
    Convert pixel coordinates to world coordinates (RA/Dec).

    Args:
        wcs: astropy.wcs.WCS object
        x_pixel: X coordinate of bbox center (in pixels)
        y_pixel: Y coordinate of bbox center (in pixels)
        width_pixel: Width of bbox (optional, for computing corner RA/Dec)
        height_pixel: Height of bbox (optional, for computing corner RA/Dec)

    Returns:
        Tuple of (ra_deg, dec_deg, (ra_min, ra_max, dec_min, dec_max)) 
        The last element (bbox_world) is None if width/height not provided
    """
    try:
        # Convert center pixel to world coordinates
        ra_center, dec_center = wcs.pixel_to_world_values(x_pixel, y_pixel)

        bbox_world = None
        if width_pixel is not None and height_pixel is not None:
            # Compute corners of the bounding box
            x_min, x_max = x_pixel - width_pixel / 2, x_pixel + width_pixel / 2
            y_min, y_max = y_pixel - height_pixel / 2, y_pixel + height_pixel / 2

            # Convert corners to world coordinates
            corners = [
                (x_min, y_min),
                (x_max, y_min),
                (x_max, y_max),
                (x_min, y_max),
            ]
            world_corners = [
                wcs.pixel_to_world_values(x, y) for x, y in corners
            ]

            ras = [ra for ra, dec in world_corners]
            decs = [dec for ra, dec in world_corners]

            bbox_world = (min(ras), max(ras), min(decs), max(decs))

        return ra_center, dec_center, bbox_world

    except Exception as e:
        print(f"Error converting pixel to world coordinates: {e}")
        return None, None, None


def extract_observation_time_from_header(header) -> Optional[datetime]:
    """
    Extract observation time from FITS header.

    Tries common keyword patterns like DATE-OBS, DATE, MJD-OBS, etc.

    Args:
        header: FITS header object

    Returns:
        datetime object or None if not found
    """
    try:
        from astropy.time import Time

        # Try common FITS date keywords
        date_keywords = ["DATE-OBS", "DATE", "MJD-OBS"]

        for keyword in date_keywords:
            if keyword in header:
                try:
                    # Parse using astropy.time.Time
                    time_obj = Time(header[keyword])
                    return time_obj.datetime
                except Exception:
                    continue

        print("Warning: Could not extract observation time from FITS header")
        return None

    except Exception as e:
        print(f"Error extracting observation time: {e}")
        return None


class DLStreakDetector(IDetector):
    def __init__(
        self,
        weights_path: str = None,
        img_size: int = 640,
        conf_thres: float = 0.25,
        iou_thres: float = 0.45,
        correlate_satellite: bool = True,
        satellite_search_radius_arcmin: float = 10.0,
        data_dir: str = "dataset",
        clean_results: bool = False,
    ):
        base_path = Path(__file__).parent.parent / "dl_streak_detect"
        self.weights_path = weights_path or str(base_path / "weights/best.pt")
        self.img_size = img_size
        self.conf_thres = conf_thres
        self.iou_thres = iou_thres
        self.correlate_satellite = correlate_satellite
        self.satellite_search_radius_arcmin = satellite_search_radius_arcmin
        self.satellite_db = SatelliteDatabaseService()
        self.data_dir = Path(data_dir)
        self.clean_results = clean_results

        # Store FITS paths and headers for later use
        self._fits_metadata: Dict[str, Dict[str, Any]] = {}

    def name(self) -> str:
        return "DL Streak Detector"

    def required_preprocessors(self) -> List[str]:
        return ["fits_to_png"]

    def _store_fits_metadata(self, fits_path: Path, header, data) -> None:
        """Store FITS metadata for later WCS conversion."""
        self._fits_metadata[fits_path.stem] = {
            "header": header,
            "image_shape": data.shape if data is not None else None,
            "fits_path": str(fits_path),
        }

    def _process_detection_with_wcs(
        self, file_stem: str, detection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance a detection with WCS world coordinates and optional satellite correlation.

        Args:
            file_stem: Stem of the FITS file (used to lookup metadata)
            detection: Detection dict with class, confidence, and box [x_center, y_center, width, height]

        Returns:
            Enhanced detection dict with world coordinates and satellite info
        """
        enhanced = detection.copy()

        # Get stored metadata
        if file_stem not in self._fits_metadata:
            return enhanced

        metadata = self._fits_metadata[file_stem]
        header = metadata.get("header")
        image_shape = metadata.get("image_shape")

        if header is None or image_shape is None:
            return enhanced

        # Extract WCS
        wcs = extract_wcs_from_fits_header(header)
        if wcs is None:
            return enhanced

        # Unpack normalized bbox: [x_center, y_center, width, height]
        bbox = detection.get("box", [])
        if len(bbox) < 4:
            return enhanced

        x_norm, y_norm, w_norm, h_norm = bbox[0], bbox[1], bbox[2], bbox[3]

        # Convert normalized coordinates to pixel coordinates
        img_height, img_width = image_shape[0], image_shape[1]
        x_pixel = x_norm * img_width
        y_pixel = y_norm * img_height
        width_pixel = w_norm * img_width
        height_pixel = h_norm * img_height

        # Convert to world coordinates
        ra_deg, dec_deg, bbox_world = pixel_bbox_to_world_coords(
            wcs, x_pixel, y_pixel, width_pixel, height_pixel
        )

        if ra_deg is not None and dec_deg is not None:
            enhanced["world_coords"] = {
                "ra_deg": ra_deg,
                "dec_deg": dec_deg,
                "ra_hms": _format_ra_hms(ra_deg),
                "dec_dms": _format_dec_dms(dec_deg),
            }

            if bbox_world is not None:
                enhanced["world_coords"]["bbox"] = {
                    "ra_min": bbox_world[0],
                    "ra_max": bbox_world[1],
                    "dec_min": bbox_world[2],
                    "dec_max": bbox_world[3],
                }

            # Attempt satellite correlation if enabled
            if self.correlate_satellite:
                obs_time = extract_observation_time_from_header(header)
                if obs_time is not None:
                    satellite_match = self.satellite_db.correlate_streak_with_satellite(
                        ra_deg,
                        dec_deg,
                        obs_time,
                        search_radius_arcmin=self.satellite_search_radius_arcmin,
                    )
                    if satellite_match:
                        enhanced["satellite_correlation"] = satellite_match

        return enhanced

    def run(self) -> Dict[str, Any]:
        """
        Run the DL Streak Detector.
        Checks the data folder, runs preprocessors, outputs into inference_data,
        then runs inference and outputs results to result_data.
        Optionally correlates streaks with satellites if correlate_satellite=True.
        """
        # Ensure directories exist
        INFERENCE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        RESULT_DATA_DIR.mkdir(parents=True, exist_ok=True)

        results_summary = []

        if not self.data_dir.exists():
            msg = f"Data directory '{self.data_dir.absolute()}' does not exist."
            print(msg)
            return {"error": msg, "streaks": []}

        files = list(self.data_dir.glob("*"))
        if not files:
            msg = f"No files found in '{self.data_dir.absolute()}'."
            print(msg)
            return {"error": msg, "streaks": []}

        # Initialize preprocessor
        fits_to_png = FitsToPng()

        for file_path in files:
            try:
                if file_path.suffix.lower() in [".fits", ".fit"]:
                    from astropy.io import fits

                    with fits.open(file_path) as hdul:
                        data = hdul[0].data
                        header = hdul[0].header
                        if data is None:
                            continue

                        # Store metadata for WCS processing
                        self._store_fits_metadata(file_path, header, data)

                        # Use FitsToPng preprocessor
                        fits_to_png.run(
                            data,
                            header,
                            INFERENCE_DATA_DIR,
                            filename=f"{file_path.stem}.png",
                        )
                elif file_path.suffix.lower() in [".jpg", ".png", ".jpeg"]:
                    png_path = INFERENCE_DATA_DIR / file_path.name
                    shutil.copy(file_path, png_path)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

        # Run inference on the inference_data folder
        opt = argparse.Namespace(
            weights=[self.weights_path],
            source=str(INFERENCE_DATA_DIR),  # Run on the whole folder
            img_size=self.img_size,
            conf_thres=self.conf_thres,
            iou_thres=self.iou_thres,
            device="",
            view_img=False,
            save_txt=True,
            save_conf=True,
            nosave=False,
            classes=None,
            agnostic_nms=False,
            augment=False,
            update=False,
            project=str(RESULT_DATA_DIR),
            name="inference",
            exist_ok=True,
            no_trace=False,
        )

        try:
            detect(opt=opt)

            # Parse results from the text files generated
            labels_dir = Path(opt.project) / opt.name / "labels"
            if labels_dir.exists():
                for label_file in labels_dir.glob("*.txt"):
                    with open(label_file, "r") as f:
                        file_results = []
                        for line in f.readlines():
                            parts = line.strip().split()
                            if len(parts) >= 6:
                                detection = {
                                    "class": str(int(parts[0])),
                                    "confidence": float(parts[5]),
                                    "box": [float(x) for x in parts[1:5]],
                                }

                                # Enhance with WCS and satellite correlation
                                detection = self._process_detection_with_wcs(
                                    label_file.stem, detection
                                )

                                file_results.append(detection)

                        results_summary.append(
                            {"file": label_file.stem, "detections": file_results}
                        )
            else:
                print(f"No label directory found at {labels_dir}. No detections made.")

            if self.clean_results:
                keep_stems = set()
                for res in results_summary:
                    stem = res["file"]
                    dets = res.get("detections", [])
                    # Keep image if there is at least one streak detected (satellite or not)
                    if len(dets) > 0:
                        keep_stems.add(stem)

                out_dir = Path(opt.project) / opt.name
                
                # Delete image files
                for ext in ["*.png", "*.jpg", "*.jpeg"]:
                    for img_path in out_dir.glob(ext):
                        if img_path.stem not in keep_stems:
                            img_path.unlink()
                
                # Delete label files
                if labels_dir.exists():
                    for txt_path in labels_dir.glob("*.txt"):
                        if txt_path.stem not in keep_stems:
                            txt_path.unlink()
                
                # Update the summary to only return the kept streaks
                results_summary = [r for r in results_summary if r["file"] in keep_stems]

        except Exception as e:
            msg = f"Inference failed: {str(e)}"
            print(msg)
            return {"error": msg, "streaks": results_summary}

        return {"streaks": results_summary}


def _format_ra_hms(ra_deg: float) -> str:
    """Convert RA in degrees to HH:MM:SS format."""
    try:
        from astropy.coordinates import Angle
        from astropy import units as u

        angle = Angle(ra_deg * u.deg)
        return angle.hms
    except Exception:
        return f"{ra_deg:.6f}°"


def _format_dec_dms(dec_deg: float) -> str:
    """Convert Dec in degrees to DD:MM:SS format."""
    try:
        from astropy.coordinates import Angle
        from astropy import units as u

        angle = Angle(dec_deg * u.deg)
        return angle.dms
    except Exception:
        return f"{dec_deg:.6f}°"
