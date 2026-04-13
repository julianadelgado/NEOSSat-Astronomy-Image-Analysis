from pathlib import Path

import astropy.units as units

from cli.config import load_config

SIGMA = 3.0
DAO_FINDER_FWHM = 3.0
DAO_FINDER_THRESHOLD = 5.0

SATURATION_PERCENTILE = 99.9
CLUSTER_EPS = 3.0
MATCH_THRESHOLD_DEFAULT = 15.0 * units.arcsec
MATCH_THRESHOLD_BRIGHT = 45.0 * units.arcsec

CANDIDATE_NOT_FOUND_STRING = "not_found"

FIGSIZE = (10, 10)
VMIN_PERCENTILE = 5
VMAX_PERCENTILE = 99

FILTERS = ["B", "V", "R", "J", "H", "K"]

TYPE_SYMBOLS = {
    "star": {"marker": "+", "color": "red"},
    "planet": {"marker": "*", "color": "green"},
    "star cluster": {"marker": "D", "color": "magenta"},
    "galaxies": {"marker": "o", "color": "blue"},
    "galaxies set": {"marker": "s", "color": "orange"},
    "spectral source": {"marker": "^", "color": "cyan"},
    "nebula": {"marker": "v", "color": "yellow"},
    "cloud": {"marker": "p", "color": "brown"},
    "Default": {"marker": "x", "color": "purple"},
}

FLUX_THRESHOLD = 1.05

config = load_config(None)

OUTPUT_DIR = Path(config.results_dir)
REPORTS_DIR = Path(config.reports_dir)


REPORTS_IMAGE_SUFFIX = "img.png"
REPORTS_MAP_SUFFIX = "map.png"
REPORTS_HEATMAP_SUFFIX = "heatmap.png"
REPORTS_PLOT_SUFFIX = "plot.png"

REPORTS_REGION_CATEGORY = "region"
REPORTS_STARS_CATEGORY = "stars"
REPORTS_MAGNITUDE_CATEGORY = "magnitude"

REPORTS_NAME_SEPARATOR = "_"

REPORTS_STARS_IMAGE_PATH = (
    f"{REPORTS_STARS_CATEGORY}{REPORTS_NAME_SEPARATOR}{REPORTS_IMAGE_SUFFIX}"
)
REPORTS_STARS_MAP_PATH = (
    f"{REPORTS_STARS_CATEGORY}{REPORTS_NAME_SEPARATOR}{REPORTS_MAP_SUFFIX}"
)
REPORTS_REGION_MAP_PATH = (
    f"{REPORTS_REGION_CATEGORY}{REPORTS_NAME_SEPARATOR}{REPORTS_MAP_SUFFIX}"
)
REPORTS_STARS_HEATMAP_PATH = (
    f"{REPORTS_STARS_CATEGORY}{REPORTS_NAME_SEPARATOR}{REPORTS_HEATMAP_SUFFIX}"
)
REPORTS_MAGNITUDE_PLOT_PATH = (
    f"{REPORTS_MAGNITUDE_CATEGORY}{REPORTS_NAME_SEPARATOR}{REPORTS_PLOT_SUFFIX}"
)
