from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from astropy.coordinates import SkyCoord

from tasks.stars.detected_star import DetectedStar
from tasks.stars.exports.map_exporter import (
    render_region_catalog_map,
    render_region_map,
)


def make_star(i=0, object_id="OBJ", otype="STAR"):
    return DetectedStar(
        x=float(i),
        y=float(i),
        coord=SkyCoord(ra=0, dec=0, unit="deg"),
        flux=10.0,
        object_id=f"{object_id}_{i}",
        otype=otype,
    )


@patch("tasks.stars.exports.map_exporter.plt")
def test_render_region_map_happy_path(mock_plt, tmp_path: Path):
    image = np.ones((10, 10))

    ax = MagicMock()
    fig = MagicMock()

    mock_plt.subplots.return_value = (fig, ax)

    stars = [
        make_star(1),
        make_star(2),
    ]

    render_region_map(image, stars, tmp_path)

    assert mock_plt.subplots.called
    assert ax.plot.called
    assert mock_plt.savefig.called
    assert mock_plt.close.called


@patch("tasks.stars.exports.map_exporter.plt")
def test_render_region_map_empty_objects(mock_plt, tmp_path: Path):
    image = np.ones((10, 10))

    ax = MagicMock()
    fig = MagicMock()

    mock_plt.subplots.return_value = (fig, ax)

    stars = []

    render_region_map(image, stars, tmp_path)

    assert mock_plt.savefig.called
    assert mock_plt.close.called


@patch("tasks.stars.exports.map_exporter.plt")
@patch("tasks.stars.exports.map_exporter.map_to_group", return_value="Default")
def test_render_region_catalog_map_happy_path(mock_group, mock_plt, tmp_path: Path):
    image = np.ones((10, 10))

    class DummyWCS:
        def world_to_pixel(self, coord):
            return (5, 5)

    class DummyObj:
        def __init__(self):
            self.coord = SkyCoord(ra=0, dec=0, unit="deg")
            self.object_id = "OBJ_1"
            self.otype = "STAR"

    catalog = [DummyObj()]

    ax = MagicMock()
    fig = MagicMock()

    mock_plt.subplots.return_value = (fig, ax)

    render_region_catalog_map(image, DummyWCS(), catalog, tmp_path)

    assert mock_plt.subplots.called
    assert ax.plot.called
    assert ax.text.called
    assert mock_plt.savefig.called
    assert mock_plt.close.called


def test_render_region_catalog_map_empty(tmp_path: Path):
    image = np.ones((10, 10))

    class DummyWCS:
        def world_to_pixel(self, coord):
            return (0, 0)

    render_region_catalog_map(image, DummyWCS(), [], tmp_path)

    assert True
