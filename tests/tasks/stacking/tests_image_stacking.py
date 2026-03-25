import os
from unittest.mock import patch

import numpy as np
from tasks.stacking.image_stacking import ImageStacking


def test_get_images_correct_mode_returns_valid_images(
    image_stacking, tmp_path, sample_fits_file, extra_fits_file
):
    """Images whose MODE header is in the allowed list must be returned."""
    result = image_stacking.get_images_correct_mode()

    fits_files = {f for f in result if f.endswith(".fits")}
    assert len(fits_files) >= 2


def test_get_images_correct_mode_excludes_wrong_mode(
    image_stacking, tmp_path, wrong_mode_fits_file
):
    """Images with a disallowed MODE header must be excluded."""
    result = image_stacking.get_images_correct_mode()

    assert os.path.basename(wrong_mode_fits_file) not in result


def test_get_images_correct_mode_empty_directory(tmp_path, mock_data_manager):
    """An empty directory must return an empty list."""
    stacking = ImageStacking(
        images_path=str(tmp_path),
        data_manager=mock_data_manager,
        date_obs="2023-01-01",
        results_dir=str(tmp_path),
    )
    result = stacking.get_images_correct_mode()

    assert result == []


def test_align_images_sets_reference_on_first_call(image_stacking, sample_fits_file):
    """The first image processed must become the reference."""
    reference_data, data_arrays = image_stacking.align_images(
        sample_fits_file, "reference.fits", None, []
    )

    assert reference_data is not None
    assert len(data_arrays) == 1


def test_align_images_skips_wrong_date(image_stacking, wrong_date_fits_file):
    """Images whose DATE-OBS does not match date_obs must be ignored."""
    reference_data, data_arrays = image_stacking.align_images(
        wrong_date_fits_file, "wrong_date.fits", None, []
    )

    assert reference_data is None
    assert len(data_arrays) == 0


def test_align_images_invalid_path(image_stacking):
    """A non-existent file path must not raise and must leave state unchanged."""
    reference_data, data_arrays = image_stacking.align_images(
        "/invalid/path/image.fits", "image.fits", None, []
    )

    assert reference_data is None
    assert data_arrays == []


def test_align_images_calls_fits_to_png_for_reference(
    image_stacking, sample_fits_file, mock_data_manager
):
    """fits_to_png must be called exactly once when the reference is set."""
    image_stacking.align_images(sample_fits_file, "reference.fits", None, [])

    mock_data_manager.fits_to_png.assert_called_once()


def test_stack_images_produces_output_file(
    image_stacking, tmp_path, sample_fits_file, extra_fits_file
):
    """stack_images must write a PNG to results_dir when ≥2 images exist."""
    with patch("astroalign.register") as mock_register:
        dummy = np.random.randint(0, 1000, (64, 64), dtype=np.float32)
        mock_register.return_value = (dummy, np.ones((64, 64), dtype=bool))

        image_stacking.stack_images()

    output_file = os.path.join(str(tmp_path), "stacked_2023-01-01.png")
    assert os.path.exists(output_file)


def test_stack_images_skips_when_single_image(
    tmp_path, mock_data_manager, sample_fits_file
):
    """stack_images must not produce an output file when only one image is available."""
    stacking = ImageStacking(
        images_path=str(tmp_path),
        data_manager=mock_data_manager,
        date_obs="2023-01-01",
        results_dir=str(tmp_path),
    )
    stacking.stack_images()

    output_file = os.path.join(str(tmp_path), "stacked_2023-01-01.png")
    assert not os.path.exists(output_file)
