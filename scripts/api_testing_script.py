import csv
import os
import random
import shutil
import time
from datetime import datetime
from typing import List, Optional

import requests
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


# =========================
# CONFIGURATION - Please keep all config values in this section for easier setup. - AB 06/04/2026
# =========================
class Config:
    CSV_FILE = "../data/result_wrpm7ldeprck4b3x.csv"
    OUTPUT_FOLDER = "../data/"
    RESULTS_FOLDER = "../results/"
    INTERVAL_SECONDS = 60

    PREPROCESSING_URL = "http://localhost:8000/preprocessing"
    HEALTH_URL = "http://localhost:8000/health"

    INFLUX_URL = ""
    INFLUX_TOKEN = ""
    INFLUX_ORG = ""
    INFLUX_BUCKET = ""

    PRODUCT_FILTER = "cord"


def ensure_directories():
    os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(Config.RESULTS_FOLDER, exist_ok=True)


def init_influx_client():
    client = InfluxDBClient(
        url=Config.INFLUX_URL, token=Config.INFLUX_TOKEN, org=Config.INFLUX_ORG
    )
    return client.write_api(write_options=SYNCHRONOUS)


def extract_obs_ids(csv_file: str, product_filter: str) -> List[str]:
    obs_ids = []

    with open(csv_file, newline="") as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)

        obs_index = find_column_index(headers, "Obs. ID")
        product_index = find_column_index(headers, "Product ID")

        for row in reader:
            if row[product_index].strip().lower() == product_filter:
                obs_ids.append(row[obs_index].strip())

    if not obs_ids:
        raise ValueError(f"No Obs. ID found with Product ID = '{product_filter}'.")

    return obs_ids


def find_column_index(headers: List[str], column_name: str) -> int:
    for i, header in enumerate(headers):
        if column_name in header:
            return i
    raise ValueError(f"Column '{column_name}' not found in CSV")


def build_fits_url(obs_id: str) -> str:
    number_part = obs_id.split("/")[-1]
    return f"https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/raven/files/cadc:NEOSSAT/NEOS_SCI_{number_part}_cord.fits"


def download_fits(obs_id: str) -> Optional[str]:
    url = build_fits_url(obs_id)
    number_part = obs_id.split("/")[-1]

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[DOWNLOAD ERROR] {number_part}: {e}")
        return None

    filepath = os.path.join(Config.OUTPUT_FOLDER, f"{number_part}.fits")
    with open(filepath, "wb") as f:
        f.write(response.content)

    print(f"[DOWNLOADED] {filepath}")
    return filepath


def call_preprocessing_api(fits_path: str) -> dict:
    response = requests.post(
        Config.PREPROCESSING_URL,
        json={
            "fits_file": os.path.abspath(fits_path),
            "preprocessors": ["star_detection", "fits_to_png"],
        },
    )
    response.raise_for_status()
    return response.json()


def extract_star_count(result: dict) -> int:
    return result["results"]["star_detection"]["stars_detected"]


def fetch_health_metrics() -> tuple[str, float]:
    response = requests.get(Config.HEALTH_URL)
    response.raise_for_status()

    data = response.json()
    return (data.get("status"), float(data.get("average_preprocessing_time_sec", 0.0)))


def archive_results():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_folder = os.path.join(Config.RESULTS_FOLDER, timestamp)
    os.makedirs(target_folder, exist_ok=True)

    for f in os.listdir(Config.RESULTS_FOLDER):
        f_path = os.path.join(Config.RESULTS_FOLDER, f)
        if os.path.isfile(f_path):
            shutil.move(f_path, os.path.join(target_folder, f))


def write_metrics(write_api, stars_detected: int, status: str, avg_time: float):
    point = (
        Point("neossat_processing")
        .tag("service_status", status)
        .field("stars_detected", stars_detected)
        .field("avg_preprocessing_time_sec", avg_time)
        .time(datetime.utcnow(), WritePrecision.S)
    )

    write_api.write(bucket=Config.INFLUX_BUCKET, org=Config.INFLUX_ORG, record=point)


def process_single_observation(obs_id: str, write_api):
    fits_file = download_fits(obs_id)
    if not fits_file:
        return

    try:
        result = call_preprocessing_api(fits_file)
        stars_detected = extract_star_count(result)

        archive_results()

        status, avg_time = fetch_health_metrics()

        print(f"[RESULT] stars={stars_detected}")
        print(f"[SERVICE] status={status}, avg_time={avg_time:.3f}s")

        write_metrics(write_api, stars_detected, status, avg_time)

    except (requests.RequestException, KeyError) as e:
        print(f"[PROCESSING ERROR] {fits_file}: {e}")


def run():
    ensure_directories()
    write_api = init_influx_client()

    obs_ids = extract_obs_ids(Config.CSV_FILE, Config.PRODUCT_FILTER)

    while True:
        obs_id = random.choice(obs_ids)
        process_single_observation(obs_id, write_api)
        time.sleep(Config.INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
