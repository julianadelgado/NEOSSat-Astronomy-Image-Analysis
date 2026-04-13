from pathlib import Path
from unittest.mock import patch
import numpy as np

from tasks.stars.exports.heatmap_exporter import render_heatmaps, generate_heatmap
from tasks.stars.detected_star import DetectedStar
from astropy.coordinates import SkyCoord


def make_star(x, y, flux=10.0):
    return DetectedStar(
        x=x,
        y=y,
        coord=SkyCoord(ra=0, dec=0, unit="deg"),
        flux=flux,
    )


def test_render_heatmaps_empty(tmp_path: Path):
    image = np.zeros((10, 10))

    render_heatmaps(image, [], tmp_path)

    assert True


@patch("tasks.stars.exports.heatmap_exporter.plt")
def test_render_heatmaps_calls_generate(mock_plt, tmp_path: Path):
    image = np.zeros((10, 10))

    stars = [
        make_star(1, 1, 10.0),
        make_star(2, 2, 20.0),
    ]

    render_heatmaps(image, stars, tmp_path)

    assert mock_plt.figure.called
    assert mock_plt.imshow.called
    assert mock_plt.savefig.called
    assert mock_plt.close.called


@patch("tasks.stars.exports.heatmap_exporter.plt")
def test_generate_heatmap_basic(mock_plt, tmp_path: Path):
    x = [0, 1, 2]
    y = [0, 1, 2]
    values = [10, 20, 30]

    output_path = tmp_path / "heatmap.png"

    generate_heatmap(
        x,
        y,
        values,
        image_shape=(10, 10),
        output_path=output_path,
        bins=5,
        title="Test Heatmap",
    )

    assert mock_plt.figure.called
    assert mock_plt.imshow.called
    assert mock_plt.colorbar.called
    assert mock_plt.savefig.called
    assert mock_plt.close.called


@patch("tasks.stars.exports.heatmap_exporter.plt")
def test_generate_heatmap_nan_handling(mock_plt, tmp_path: Path):
    x = [0]
    y = [0]
    values = [0]

    output_path = tmp_path / "heatmap.png"

    generate_heatmap(
        x,
        y,
        values,
        image_shape=(5, 5),
        output_path=output_path,
        bins=2,
    )

    assert mock_plt.savefig.called
