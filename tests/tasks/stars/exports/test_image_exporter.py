from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from astropy.coordinates import SkyCoord

from tasks.stars.detected_star import DetectedStar
from tasks.stars.exports.image_exporter import render_region_image


def make_star(x, y, object_id=None):
    return DetectedStar(
        x=x,
        y=y,
        coord=SkyCoord(ra=0, dec=0, unit="deg"),
        flux=10.0,
        object_id=object_id,
    )


@patch("tasks.stars.exports.image_exporter.plt")
def test_render_region_image_matplotlib_flow(mock_plt, tmp_path: Path):

    image = np.ones((10, 10))

    wcs = MagicMock()

    ax = MagicMock()
    fig = MagicMock()

    mock_plt.figure.return_value = fig
    mock_plt.subplot.return_value = ax

    stars = [
        make_star(1, 1, "OBJ_1"),
        make_star(2, 2, None),
    ]

    render_region_image(image, wcs, stars, tmp_path)

    assert mock_plt.figure.called
    assert mock_plt.subplot.called
    assert ax.imshow.called
    assert ax.plot.called
    assert ax.text.called
    assert mock_plt.savefig.called
    assert mock_plt.close.called
