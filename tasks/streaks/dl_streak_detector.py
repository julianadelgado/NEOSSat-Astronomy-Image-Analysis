import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.append(str(Path(__file__).parent / "dl_streak_detect"))
from cli.config import load_config
from preprocessing.preprocessors.fits_to_png import FitsToPng
from services.satellite_db_service import SatelliteDatabaseService
from tasks.streaks.dl_streak_detect.detect import detect

from .IDetector import IDetector

config = load_config(None)

DATA_DIR = Path(config.data_dir)
INFERENCE_DATA_DIR = Path("inference_data")  # unique folder for this detector
RESULT_DATA_DIR = Path(config.results_dir)
REPORTS_DIR = Path(config.reports_dir)


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
            world_corners = [wcs.pixel_to_world_values(x, y) for x, y in corners]

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
        data_dir: str = None,
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
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
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
            # Convert numpy 0-d arrays to native Python floats for JSON serialization
            ra_deg_float = float(ra_deg)
            dec_deg_float = float(dec_deg)

            enhanced["world_coords"] = {
                "ra_deg": ra_deg_float,
                "dec_deg": dec_deg_float,
                "ra_hms": _format_ra_hms(ra_deg_float),
                "dec_dms": _format_dec_dms(dec_deg_float),
            }

            if bbox_world is not None:
                enhanced["world_coords"]["bbox"] = {
                    "ra_min": float(bbox_world[0]),
                    "ra_max": float(bbox_world[1]),
                    "dec_min": float(bbox_world[2]),
                    "dec_max": float(bbox_world[3]),
                }

            # Always attempt satellite correlation
            obs_time = extract_observation_time_from_header(header)
            if obs_time is not None:
                satellite_match = self.satellite_db.correlate_streak_with_satellite(
                    ra_deg_float,
                    dec_deg_float,
                    obs_time,
                    search_radius_arcmin=self.satellite_search_radius_arcmin,
                )
                if satellite_match:
                    enhanced["satellite_correlation"] = satellite_match

        return enhanced

    def _generate_markdown_report(
        self, results_summary: List[Dict[str, Any]], result_dir: Path
    ) -> None:
        has_content = any(len(res.get("detections", [])) > 0 for res in results_summary)
        if not has_content:
            return

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = (
            REPORTS_DIR / f"streak_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )

        lines = ["# Streak Detection Report\n"]
        lines.append(f"Generated at: {datetime.now().isoformat()}\n")

        for res in results_summary:
            stem = res["file"]
            dets = res.get("detections", [])
            if not dets:
                continue

            lines.append(f"## File: {stem}\n")

            # Try to find the image
            img_path = None
            for ext in [".png", ".jpg", ".jpeg"]:
                candidate = result_dir / f"{stem}{ext}"
                if candidate.exists():
                    img_path = candidate
                    break

            if img_path:
                lines.append(f"![{stem}]({img_path.absolute().as_posix()})\n")

            for i, det in enumerate(dets):
                lines.append(f"### Detection {i+1}")
                lines.append(f"- Confidence: {det.get('confidence', 0):.2f}")
                if "world_coords" in det:
                    wc = det["world_coords"]
                    lines.append(
                        f"- RA: {wc.get('ra_hms', wc.get('ra_deg'))} (Deg: {wc.get('ra_deg')})"
                    )
                    lines.append(
                        f"- Dec: {wc.get('dec_dms', wc.get('dec_deg'))} (Deg: {wc.get('dec_deg')})"
                    )

                if "satellite_correlation" in det:
                    sat = det["satellite_correlation"]
                    lines.append(f"#### Correlated Satellite")
                    lines.append(f"- Name: {sat.get('name')}")
                    lines.append(f"- Catalog ID: {sat.get('catalog_id')}")
                    lines.append(
                        f"- Separation: {sat.get('separation_arcmin', 0):.2f} arcmin"
                    )
                    lines.append(f"- Confidence: {sat.get('confidence', 0):.2f}")
                lines.append("")

            lines.append("\n---\n")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Report generated: {report_path.absolute()}")

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
            no_trace=True,
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

                        if file_results:
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
                results_summary = [
                    r for r in results_summary if r["file"] in keep_stems
                ]

        except Exception as e:
            msg = f"Inference failed: {str(e)}"
            print(msg)
            return {"error": msg, "streaks": results_summary}
        finally:
            if INFERENCE_DATA_DIR.exists():
                shutil.rmtree(INFERENCE_DATA_DIR, ignore_errors=True)

            # Clean up skyfield downloaded TLE files
            gp_php_path = Path("gp.php")
            if gp_php_path.exists():
                gp_php_path.unlink()

        self._generate_markdown_report(results_summary, Path(opt.project) / opt.name)

        return {"streaks": results_summary}


def _format_ra_hms(ra_deg: float) -> str:
    """Convert RA in degrees to HH:MM:SS format."""
    try:
        from astropy import units as u
        from astropy.coordinates import Angle

        angle = Angle(ra_deg * u.deg)
        return angle.hms
    except Exception:
        return f"{ra_deg:.6f}°"


def _format_dec_dms(dec_deg: float) -> str:
    """Convert Dec in degrees to DD:MM:SS format."""
    try:
        from astropy import units as u
        from astropy.coordinates import Angle

        angle = Angle(dec_deg * u.deg)
        return angle.dms
    except Exception:
        return f"{dec_deg:.6f}°"
