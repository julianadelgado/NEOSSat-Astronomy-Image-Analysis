import csv
import random
import requests
import time
import os


CSV_FILE = "../data/result_wrpm7ldeprck4b3x.csv"
OUTPUT_FOLDER = "../data/"
INTERVAL_SECONDS = 10

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

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
    number_part = obs_id.split('/')[-1]  # Use to extract numbers : 2025071222825 for example - AB 30/03/2026
    url = f"https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/raven/files/cadc:NEOSSAT/NEOS_SCI_{number_part}_cord.fits"

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Erreur lors du téléchargement de {number_part}: {e}")
        return

    filename = os.path.join(OUTPUT_FOLDER, f"{number_part}.fits")
    with open(filename, 'wb') as f:
        f.write(response.content)

    print(f"Téléchargé : {filename}")


while True:
    selected_obs_id = random.choice(obs_ids)
    download_image(selected_obs_id)
    time.sleep(INTERVAL_SECONDS)
