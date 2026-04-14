from pathlib import Path
from unittest.mock import MagicMock, patch

from astropy.coordinates import SkyCoord

from tasks.stars.constants import FILTERS
from tasks.stars.detected_star import DetectedStar
from tasks.stars.exports.magnitude_data_exporter import render_magnitude_plot


def make_star(i, object_id="OBJ"):
    return DetectedStar(
        x=float(i),
        y=float(i),
        coord=SkyCoord(ra=0, dec=0, unit="deg"),
        flux=10.0,
        magnitude_obs=10.0 + i,
        object_id=f"{object_id}_{i}",
        mag_b=1.0 + i,
        mag_v=2.0 + i,
        mag_r=3.0 + i,
        mag_j=4.0 + i,
        mag_h=5.0 + i,
        mag_k=6.0 + i,
    )


@patch("tasks.stars.exports.magnitude_data_exporter.plt")
def test_render_magnitude_plot_happy_path(mock_plt, tmp_path: Path):
    stars = [make_star(0), make_star(1)]

    ax = MagicMock()
    fig = MagicMock()

    mock_plt.subplots.return_value = (fig, ax)

    render_magnitude_plot(stars, tmp_path)

    assert mock_plt.subplots.called
    assert ax.scatter.called
    assert ax.set_xlabel.called
    assert ax.set_ylabel.called
    assert ax.set_title.called
    assert ax.legend.called
    assert mock_plt.tight_layout.called
    assert mock_plt.savefig.called
    assert mock_plt.close.called


def test_render_magnitude_plot_empty(tmp_path: Path):
    render_magnitude_plot([], tmp_path)

    assert True


@patch("tasks.stars.exports.magnitude_data_exporter.plt")
def test_render_magnitude_plot_filters(mock_plt, tmp_path: Path):
    stars = [
        make_star(0, "STAR"),
        make_star(1, "STAR"),
    ]

    ax = MagicMock()
    fig = MagicMock()

    mock_plt.subplots.return_value = (fig, ax)

    render_magnitude_plot(stars, tmp_path)

    colors_calls = ax.scatter.call_args_list

    assert len(colors_calls) >= len(FILTERS)
