import os
import shutil
from pathlib import Path

import typer
from astropy.io import fits

from cli.validator import validate_data_directory, validate_email
from handlers.data_manager import DataManager
from handlers.fits_handler import FitsHandler
from tasks.stacking.image_stacking import ImageStacking
from tasks.stars.star_detection import StarDetection
from tasks.streaks.dl_streak_detector import DLStreakDetector
from services.email_service import EmailService

from .config import load_config

app = typer.Typer()
svc = EmailService()

@app.command()
def main(
    data_dir: str = typer.Option(
        None,
        "--data-dir",
        "-d",
        help="Path to directory containing FITS files",
        callback=validate_data_directory,
    ),
    email: str = typer.Option(
        None,
        "--email",
        "-e",
        help="Email address to receive results",
        callback=validate_email,
    ),
    stars: bool = typer.Option(False, "--stars", "-s", help="Run star detection"),
    image_stacking: bool = typer.Option(
        False, "--image-stacking", "-i", help="Run image stacking"
    ),
    streaks: bool = typer.Option(False, "--streaks", "-k", help="Run streak detection"),
    results_dir: str = typer.Option(
        None,
        "--results-dir",
        "-r",
        help="Path to directory to save results (default: ./results)",
    ),
    reports_dir: str = typer.Option(
        None,
        "--reports-dir",
        "-R",
        help="Path to directory to save reports (default: ./reports)",
    ),
    wrong_mode_dir: str = typer.Option(
        None,
        "--wrong-mode-dir",
        "-w",
        help="Path to directory to save FITS files in wrong mode (default: ./wrong_mode)",
    ),
):
    print("Welcome to the NEOSSat Astronomy Image Analysis!")
    cfg = load_config(None)

    # Check raw config to see if keys were explicitly provided
    config_keys = {}
    default_config = Path("config.yaml")
    if default_config.exists():
        import yaml

        with open(default_config) as f:
            config_keys = yaml.safe_load(f) or {}

    if data_dir:
        cfg.data_dir = data_dir
    elif "data_dir" not in config_keys:
        cfg.data_dir = typer.prompt(
            "Enter the path to the data directory", default=cfg.data_dir
        )

    if email:
        cfg.email = email
    elif "email" not in config_keys:
        cfg.email = typer.prompt(
            "Enter a valid email address to receive results",
            default=cfg.email if cfg.email else None,
        )
    if results_dir:
        cfg.results_dir = results_dir
    if reports_dir:
        cfg.reports_dir = reports_dir
    if wrong_mode_dir:
        cfg.wrong_mode_dir = wrong_mode_dir

    # If neither flag is set, run everything
    run_all = not (stars or image_stacking or streaks)
    run_stars = stars or run_all
    run_image_stacking = image_stacking or run_all
    run_streaks = streaks or run_all

    for filename in os.listdir(cfg.data_dir):
        if filename.endswith(".fits"):
            file_path = os.path.join(cfg.data_dir, filename)
            data_manager = DataManager(file_path)
            if data_manager.is_fits_correct_mode():
                # TODO verify order of call operations
                if run_image_stacking:
                    print("Running image stacking...")
                    # TODO Should ImageStacking be a preprocessor?
                    sky_coord = data_manager.get_coordinates()
                    date_obs = data_manager.get_images_same_date()

                    if sky_coord and date_obs:
                        print(f"Coordinates Found: {sky_coord.to_string('hmsdms')}")
                        print(f"Observation Date: {date_obs}")

                        clean_name = filename.replace(".fits", "")
                        os.makedirs(clean_name, exist_ok=True)

                        downloader = FitsHandler(sky_coord, date_obs)
                        downloader.download_images_to_directory(clean_name)
                        preprocessor = ImageStacking(clean_name, data_manager, date_obs)
                        preprocessor.stack_images()
                        print(f"Cleaning up temporary folder: {clean_name} ")
                        shutil.rmtree(clean_name)
                    data_manager.fits_image.close()

                if run_stars:
                    print("Running star detection...")
                    detector = StarDetection()
                    fits_path = Path(cfg.data_dir) / filename
                    output_dir = Path(cfg.results_dir) / filename.replace(".fits", "")
                    output_dir.mkdir(parents=True, exist_ok=True)

                    image = fits.getdata(fits_path)
                    header = fits.getheader(fits_path)
                    detector.run(image, header, output_dir)

            else:
                print(
                    f"Moving {filename} to wrong mode directory: {cfg.wrong_mode_dir}"
                )
                data_manager.fits_image.close()
                os.makedirs(cfg.wrong_mode_dir, exist_ok=True)
                shutil.move(file_path, os.path.join(cfg.wrong_mode_dir, filename))

    # Run streak detection on the whole directory once
    if run_streaks:
        print("Running streak detection on directory...")
        detector = DLStreakDetector(data_dir=cfg.data_dir, clean_results=True)
        detector.run()

    completed_tasks = []
    if run_image_stacking:
        completed_tasks.append("image_stacking")
    if run_stars:
        completed_tasks.append("stars")
    if run_streaks:
        completed_tasks.append("streaks")
    svc.send_completion_notification(cfg.email, completed_tasks)

if __name__ == "__main__":
    main()
