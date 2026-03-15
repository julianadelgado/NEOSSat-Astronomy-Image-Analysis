import os
from pathlib import Path

import typer

from acquisition.data_manager import DataManager
from acquisition.fits_handler import FitsHandler
from acquisition.image_stacking import ImageStacking
from cli.validator import validate_data_directory, validate_email
from preprocessing.metrics import Metrics
from preprocessing.pipeline import Pipeline
from preprocessing.preprocessors.star_detection import StarDetection

from .config import load_config

app = typer.Typer()


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
):
    print("Welcome to the NEOSSat Astronomy Image Analysis!")
    cfg = load_config(None)

    if data_dir:
        cfg.data_dir = data_dir
    else:
        cfg.data_dir = typer.prompt(
            "Enter the path to the data directory", default=cfg.data_dir
        )
    if email:
        cfg.email = email
    else:
        cfg.email = typer.prompt(
            "Enter a valid email address to receive results", default=cfg.email
        )
    if results_dir:
        cfg.results_dir = results_dir
    if reports_dir:
        cfg.reports_dir = reports_dir

    # If neither flag is set, run everything
    run_all = not (stars or image_stacking or streaks)
    run_stars = stars or run_all
    run_image_stacking = image_stacking or run_all
    run_streaks = streaks or run_all

    # TODO verify order of call operations
    if run_image_stacking:
        print("Running image stacking...")
        # TODO Should ImageStacking be a preprocessor?
        for filename in os.listdir(cfg.data_dir):
            if filename.endswith(".fits"):
                file_path = os.path.join(cfg.data_dir, filename)
                print(f"\nProcessing: {filename}")

                data_manager = DataManager(file_path)
                sky_coord = data_manager.get_coordinates()
                date_obs = data_manager.get_images_same_date()

                if sky_coord and date_obs:
                    print(f"Coordinates Found: {sky_coord.to_string('hmsdms')}")
                    print(f"Observation Date: {date_obs}")

                    clean_name = filename.replace(".fits", "")
                    os.makedirs(clean_name, exist_ok=True)

                    downloader = FitsHandler(sky_coord, date_obs)
                    downloader.download_images_to_directory(clean_name)
                    preprocessor = ImageStacking(clean_name, data_manager, date_obs, cfg.results_dir)
                    preprocessor.stack_images()
                data_manager.fits_image.close()
                
    if run_stars:
        print("Running star detection...")
        # TODO verify star detection call
        pipeline = Pipeline([StarDetection()], Metrics())
        for filename in os.listdir(cfg.data_dir):
            if filename.endswith(".fits"):
                fits_path = Path(cfg.data_dir) / filename
                output_dir = Path(cfg.data_dir) / filename.replace(".fits", "")
                results = pipeline.run(fits_path, ["star_detection"], output_dir)
                print(f"{filename}: {results}")

    if run_streaks:
        print("Running streak detection...")
        # TODO Call streak detection function here


if __name__ == "__main__":
    main()
