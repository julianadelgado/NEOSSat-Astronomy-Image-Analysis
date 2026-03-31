import os
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

# Must be set before importing cli.main, since EmailService is instantiated at module level
os.environ.setdefault("SMTP_SERVER", "smtp.test")
os.environ.setdefault("SMTP_USER", "test@test.com")
os.environ.setdefault("SMTP_PASSWORD", "test_password")

from cli.main import app  # noqa: E402

runner = CliRunner()

valid_dir_patch = patch("cli.validator.os.path.exists", return_value=True)
listdir_patch = patch("cli.main.os.listdir", return_value=["image.fits"])
fits_patches = [
    patch("cli.main.fits.getdata", return_value=MagicMock()),
    patch("cli.main.fits.getheader", return_value=MagicMock()),
    patch("cli.main.Path.mkdir"),
]


@patch("cli.main.ImageStacking")
@patch("cli.main.DataManager")
@patch("cli.main.FitsHandler")
@patch("cli.main.shutil.rmtree")
@patch("cli.main.os.makedirs")
@listdir_patch
@patch("cli.main.load_config")
@valid_dir_patch
def test_image_stacking_flag_only_runs_image_stacking(
    mock_exists,
    mock_config,
    mock_listdir,
    mock_makedirs,
    mock_rmtree,
    mock_fits_handler,
    mock_data_manager,
    mock_image_stacking,
):
    mock_config.return_value = MagicMock(
        data_dir="/fake", results_dir="/fake/results", email="test@example.com"
    )
    mock_data_manager.return_value.get_coordinates.return_value = MagicMock()
    mock_data_manager.return_value.get_images_same_date.return_value = MagicMock()

    result = runner.invoke(
        app, ["--data-dir", "/fake", "--email", "test@example.com", "--image-stacking"]
    )

    assert result.exit_code == 0
    mock_image_stacking.assert_called_once()


@patch("cli.main.StarDetection")
@patch("cli.main.DataManager")
@patch("cli.main.fits.getheader", return_value=MagicMock())
@patch("cli.main.fits.getdata", return_value=MagicMock())
@patch("cli.main.Path.mkdir")
@listdir_patch
@patch("cli.main.load_config")
@patch("cli.main.DataManager")
@valid_dir_patch
def test_stars_flag_only_runs_star_detection(
    mock_exists,
    mock_data_manager,
    mock_config,
    mock_listdir,
    mock_mkdir,
    mock_getdata,
    mock_getheader,
    mock_dm,
    mock_star_detection,
):
    mock_config.return_value = MagicMock(
        data_dir="/fake", results_dir="/fake/results", email="test@example.com"
    )

    result = runner.invoke(
        app, ["--data-dir", "/fake", "--email", "test@example.com", "--stars"]
    )

    assert result.exit_code == 0
    mock_star_detection.assert_called_once()


@patch("cli.main.DLStreakDetector")
@listdir_patch
@patch("cli.main.load_config")
@patch("cli.main.DataManager")
@valid_dir_patch
def test_streaks_flag_only_runs_streak_detection(
    mock_exists, mock_data_manager, mock_config, mock_listdir, mock_streak_detector
):
    mock_config.return_value = MagicMock(
        data_dir="/fake", results_dir="/fake/results", email="test@example.com"
    )

    result = runner.invoke(
        app, ["--data-dir", "/fake", "--email", "test@example.com", "--streaks"]
    )

    assert result.exit_code == 0
    mock_streak_detector.assert_called_once()


@patch("cli.main.DLStreakDetector")
@patch("cli.main.ImageStacking")
@patch("cli.main.DataManager")
@patch("cli.main.FitsHandler")
@patch("cli.main.shutil.rmtree")
@patch("cli.main.os.makedirs")
@patch("cli.main.StarDetection")
@patch("cli.main.fits.getheader", return_value=MagicMock())
@patch("cli.main.fits.getdata", return_value=MagicMock())
@patch("cli.main.Path.mkdir")
@listdir_patch
@patch("cli.main.load_config")
@valid_dir_patch
def test_no_flags_runs_all_tasks(
    mock_exists,
    mock_config,
    mock_listdir,
    mock_mkdir,
    mock_getdata,
    mock_getheader,
    mock_star_detection,
    mock_makedirs,
    mock_rmtree,
    mock_fits_handler,
    mock_data_manager,
    mock_image_stacking,
    mock_streak_detector,
):
    mock_config.return_value = MagicMock(
        data_dir="/fake", results_dir="/fake/results", email="test@example.com"
    )
    mock_data_manager.return_value.get_coordinates.return_value = MagicMock()
    mock_data_manager.return_value.get_images_same_date.return_value = MagicMock()

    result = runner.invoke(app, ["--data-dir", "/fake", "--email", "test@example.com"])

    assert result.exit_code == 0
    mock_star_detection.assert_called_once()
    mock_image_stacking.assert_called_once()
    mock_streak_detector.assert_called_once()


@patch("cli.main.DataManager")
@listdir_patch
@patch("cli.main.load_config")
@valid_dir_patch
def test_notification_sent_after_tasks_complete(
    mock_exists,
    mock_config,
    mock_listdir,
    mock_data_manager,
):
    mock_config.return_value = MagicMock(
        data_dir="/fake", results_dir="/fake/results", email="test@example.com"
    )

    with patch("cli.main.svc.send_completion_notification") as mock_notify:
        with (
            patch("cli.main.DLStreakDetector"),
            patch("cli.main.StarDetection"),
            patch("cli.main.fits.getdata", return_value=MagicMock()),
            patch("cli.main.fits.getheader", return_value=MagicMock()),
            patch("cli.main.Path.mkdir"),
        ):
            result = runner.invoke(
                app, ["--data-dir", "/fake", "--email", "test@example.com"]
            )

    assert result.exit_code == 0
    mock_notify.assert_called_once_with(
        "test@example.com", ["image_stacking", "stars", "streaks"]
    )


@patch("cli.main.DataManager")
@listdir_patch
@patch("cli.main.load_config")
@valid_dir_patch
def test_notification_sent_with_stars_flag(
    mock_exists,
    mock_config,
    mock_listdir,
    mock_data_manager,
):
    mock_config.return_value = MagicMock(
        data_dir="/fake", results_dir="/fake/results", email="test@example.com"
    )

    with patch("cli.main.svc.send_completion_notification") as mock_notify:
        with (
            patch("cli.main.StarDetection"),
            patch("cli.main.fits.getdata", return_value=MagicMock()),
            patch("cli.main.fits.getheader", return_value=MagicMock()),
            patch("cli.main.Path.mkdir"),
        ):
            result = runner.invoke(
                app, ["--data-dir", "/fake", "--email", "test@example.com", "--stars"]
            )

    assert result.exit_code == 0
    mock_notify.assert_called_once_with("test@example.com", ["stars"])


@patch("cli.main.DataManager")
@listdir_patch
@patch("cli.main.load_config")
@valid_dir_patch
def test_notification_sent_with_streaks_flag(
    mock_exists,
    mock_config,
    mock_listdir,
    mock_data_manager,
):
    mock_config.return_value = MagicMock(
        data_dir="/fake", results_dir="/fake/results", email="test@example.com"
    )

    with patch("cli.main.svc.send_completion_notification") as mock_notify:
        with patch("cli.main.DLStreakDetector"):
            result = runner.invoke(
                app,
                ["--data-dir", "/fake", "--email", "test@example.com", "--streaks"],
            )

    assert result.exit_code == 0
    mock_notify.assert_called_once_with("test@example.com", ["streaks"])


@patch("cli.main.DataManager")
@listdir_patch
@patch("cli.main.load_config")
@valid_dir_patch
def test_notification_sent_with_image_stacking_flag(
    mock_exists,
    mock_config,
    mock_listdir,
    mock_data_manager,
):
    mock_config.return_value = MagicMock(
        data_dir="/fake", results_dir="/fake/results", email="test@example.com"
    )
    mock_data_manager.return_value.get_coordinates.return_value = MagicMock()
    mock_data_manager.return_value.get_images_same_date.return_value = MagicMock()

    with patch("cli.main.svc.send_completion_notification") as mock_notify:
        with (
            patch("cli.main.ImageStacking"),
            patch("cli.main.FitsHandler"),
            patch("cli.main.shutil.rmtree"),
            patch("cli.main.os.makedirs"),
        ):
            result = runner.invoke(
                app,
                [
                    "--data-dir",
                    "/fake",
                    "--email",
                    "test@example.com",
                    "--image-stacking",
                ],
            )

    assert result.exit_code == 0
    mock_notify.assert_called_once_with("test@example.com", ["image_stacking"])
