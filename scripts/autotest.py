import csv
import random
import requests
import time
import os
import json
import shutil
from datetime import datetime

CSV_FILE = "../data/result_wrpm7ldeprck4b3x.csv"
OUTPUT_FOLDER = "../data/"
INTERVAL_SECONDS = 10
RESULTS_FOLDER = "../results/"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

obs_ids = []
with open(CSV_FILE, newline='') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader)

    obs_index = None
    product_index = None
    for i, h in enumerate(headers):
        if "Obs. ID" in h:
            obs_index = i
        if "Product ID" in h:
            product_index = i
    if obs_index is None or product_index is None:
        raise ValueError("Impossible de trouver les colonnes Obs. ID ou Product ID dans le CSV")

    for row in reader:
        product_id = row[product_index].strip().lower()
        if product_id == "cord":
            obs_id = row[obs_index].strip()
            obs_ids.append(obs_id)

if not obs_ids:
    raise ValueError("Aucune Obs. ID trouvée avec Product ID = 'cord'.")


def download_image(obs_id):
    number_part = obs_id.split('/')[-1]
    url = f"https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/raven/files/cadc:NEOSSAT/NEOS_SCI_{number_part}_cord.fits"

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Erreur lors du téléchargement de {number_part}: {e}")
        return None

    filename = os.path.join(OUTPUT_FOLDER, f"{number_part}.fits")
    with open(filename, 'wb') as f:
        f.write(response.content)

    print(f"Téléchargé : {filename}")
    return filename


while True:
    selected_obs_id = random.choice(obs_ids)
    fits_file = download_image(selected_obs_id)
    if fits_file:
        try:
            fits_file_abs = os.path.abspath(fits_file)
            response = requests.post(
                "http://localhost:8000/preprocessing",
                json={
                    "fits_file": fits_file_abs,
                    "preprocessors": ["star_detection", "fits_to_png"]
                }
            )
            response.raise_for_status()
            result = response.json()
            print(json.dumps(result, indent=2))

            stars_detected = result["results"]["star_detection"]["stars_detected"]
            print(f"Étoiles détectées : {stars_detected}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_folder = os.path.join(RESULTS_FOLDER, timestamp)
            os.makedirs(target_folder, exist_ok=True)
            for f in os.listdir(RESULTS_FOLDER):
                f_path = os.path.join(RESULTS_FOLDER, f)
                if os.path.isfile(f_path):
                    shutil.move(f_path, os.path.join(target_folder, f))

        except requests.RequestException as e:
            print(f"Erreur lors de l'appel de preprocessing pour {fits_file}: {e}")
        except KeyError as e:
            print(f"Clé manquante dans la réponse : {e}")

    time.sleep(INTERVAL_SECONDS)
