import os
from pathlib import Path

import astroalign as aa
import numpy as np
from astropy.io import fits
from PIL import Image

from cli.config import load_config
from handlers.data_manager import DataManager
from services.report_service import (
    ReportData,
    ReportSection,
    ReportService,
    ReportTable,
)

config = load_config(None)

REPORTS_DIR = Path(config.reports_dir)
RESULTS_DIR = Path(config.results_dir)


class ImageStacking:
    def __init__(self, images_path, data_manager, date_obs):
        self.images_path = images_path
        self.data_manager = data_manager
        self.date_obs = date_obs
        self.results_dir = RESULTS_DIR

    def align_images(self, img_path, img_name, reference_data, data_arrays):
        try:
            with fits.open(img_path) as img_fits:
                header = img_fits[0].header
                img_date = header.get("DATE-OBS", "").split("T")[0]

                if img_date != self.date_obs:
                    return reference_data, data_arrays

                current_data = img_fits[0].data.astype(np.float32)

                if reference_data is None:
                    before_path = os.path.join(
                        self.results_dir, f"before_{self.date_obs}.png"
                    )
                    self.data_manager.fits_to_png(before_path)

                    reference_data = current_data
                    data_arrays.append(current_data)
                else:
                    try:
                        aligned_image, footprint = aa.register(
                            current_data, reference_data
                        )
                        data_arrays.append(aligned_image)
                    except Exception as e:
                        print(f"Error aligning image {img_name}: {e}")
        except Exception as e:
            print(f"Error opening FITS file {img_name}: {e}")
        return reference_data, data_arrays, img_name

    def stack_images(self):
        PERCENTILE_LOWER_BOUND = 40
        PERCENTILE_UPPER_BOUND = 99.9
        original_image_path = self.data_manager.file_path
        all_images = [f for f in os.listdir(self.images_path) if f.endswith(".fits")]
        self.stacked_images = []
        stacked_images = self.stacked_images

        data_arrays = []
        reference_data = None

        reference_data, data_arrays, _ = self.align_images(
            original_image_path,
            os.path.basename(original_image_path),
            reference_data,
            data_arrays,
        )

        for img_name in all_images:
            img_path = os.path.join(self.images_path, img_name)
            img_data_manager = DataManager(img_path)
            if not img_data_manager.is_fits_correct_mode():
                continue
            reference_data, data_arrays, curr_img_name = self.align_images(
                img_path, img_name, reference_data, data_arrays
            )
            stacked_images.append(img_data_manager.get_observation_ids(curr_img_name))

        if len(data_arrays) > 1:
            print(f"Stacking {len(stacked_images)} images for {self.date_obs}...")

            stacked_data = np.nanmax(data_arrays, axis=0)

            vmin = np.percentile(stacked_data, PERCENTILE_LOWER_BOUND)
            vmax = np.percentile(stacked_data, PERCENTILE_UPPER_BOUND)
            if vmax <= vmin:
                print("Skipping stacking due to invalid percentile bounds.")
                return
            stacked_scaled = np.clip(
                (stacked_data - vmin) / (vmax - vmin) * 255, 0, 255
            )
            stacked_output = stacked_scaled.astype(np.uint8)

            stacked_image = Image.fromarray(stacked_output)
            output_path = os.path.join(self.results_dir, f"stacked_{self.date_obs}.png")
            stacked_image.save(output_path)
            print(f"Stacked image saved: {output_path}")
        else:
            print(f"Only one image for date {self.date_obs}, skipping stacking.")

    def _build_report_section(self, stacked_images) -> ReportSection:
        stacking_table = ReportTable(
            headers=["Observation IDs"],
            rows=[[obs_id] for obs_id in stacked_images],
        )
        return ReportSection(
            title=f"Results for {self.date_obs}",
            content=f"Stacked image created for date {self.date_obs}.",
            images=[
                p
                for p in [Path(self.results_dir) / f"stacked_{self.date_obs}.png"]
                if p.exists()
            ],
            tables=[stacking_table],
        )
