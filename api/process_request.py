from typing import Optional

from pydantic import BaseModel


class ProcessRequest(BaseModel):
    fits_file: str
    processors: Optional[list[str]] = None

    run_streak_detection: bool = False
    run_star_detection: bool = False
    run_image_stacking: bool = False

    # Optional parameters for streak detection
    streak_detection_conf_threshold: Optional[float] = 0.25
    streak_detection_iou_threshold: Optional[float] = 0.45

    # Optional parameters for image stacking
    images_path: Optional[str] = None
    date_obs: Optional[str] = None
