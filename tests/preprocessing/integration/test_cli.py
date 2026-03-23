from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from cli.main import app

runner = CliRunner()

@patch("cli.main.StarDetection")
@patch("cli.main.os.listdir", return_value=[]) 
@patch("cli.main.load_config")
def test_stars_flag_only_runs_star_detection(mock_config, mock_listdir, mock_star_detection):
    mock_config.return_value = MagicMock(data_dir="/fake_data_dir", results_dir="/fake_results_dir", report_dir="/fake_reports_dir", email="test@example.com")
    result = runner.invoke(app, ["--data-dir", "/fake_data_dir", "--email", "test@example.com", "--stars"])
    
    assert result.exit_code == 0
    mock_star_detection.assert_called_once()
    mock_star

@patch("cli.main.ImageStacking")
@patch("cli.main.os.listdir", return_value=[]) 
@patch("cli.main.load_config")
def test_stars_flag_only_runs_star_detection(mock_config, mock_listdir, mock_star_detection):
    mock_config.return_value = MagicMock(data_dir="/fake_data_dir", results_dir="/fake_results_dir", report_dir="/fake_reports_dir", email="test@example.com")
    result = runner.invoke(app, ["--data-dir", "/fake_data_dir", "--email", "test@example.com", "--stars"])
    
    assert result.exit_code == 0
    mock_star_detection.assert_called_once()

@patch("cli.main.ImageStacking")
@patch("cli.main.os.listdir", return_value=[]) 
@patch("cli.main.load_config")
def test_stars_flag_only_runs_star_detection(mock_config, mock_listdir, mock_star_detection):
    mock_config.return_value = MagicMock(data_dir="/fake_data_dir", results_dir="/fake_results_dir", report_dir="/fake_reports_dir", email="test@example.com")
    result = runner.invoke(app, ["--data-dir", "/fake_data_dir", "--email", "test@example.com", "--stars"])
    
    assert result.exit_code == 0
    mock_star_detection.assert_called_once()