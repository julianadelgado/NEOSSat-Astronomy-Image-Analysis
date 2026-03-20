import ftplib
import os
import sys
from pathlib import Path

import requests
from astropy import units as u
from astropy.coordinates import SkyCoord
from astroquery.cadc import Cadc
from astroquery.skyview import SkyView
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

# --- Threads ---


class SkyViewThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, target, survey, radius, data_folder):
        super().__init__()
        self.target = target
        self.survey = survey
        self.radius = radius
        self.data_folder = data_folder

    def run(self):
        try:
            hdul_list = SkyView.get_images(
                position=self.target, survey=[self.survey], radius=self.radius * u.deg
            )

            if not hdul_list:
                self.finished.emit(False, "No images found for this target/survey.")
                return

            hdul = hdul_list[0]
            safe_target = "".join([c if c.isalnum() else "_" for c in self.target])
            safe_survey = "".join([c if c.isalnum() else "_" for c in self.survey])
            filename = f"{safe_target}_{safe_survey}.fits"
            filepath = os.path.join(self.data_folder, filename)

            hdul.writeto(filepath, overwrite=True)
            self.finished.emit(True, f"Saved to {filename}")

        except Exception as e:
            self.finished.emit(False, str(e))


class CadcSearchThread(QThread):
    """Queries CADC for NEOSSAT data metadata"""

    results_found = pyqtSignal(
        list, object
    )  # list of dicts, and raw table (optional, or just list)
    error_occurred = pyqtSignal(str)

    def __init__(self, target, radius, is_raw_degrees=False):
        super().__init__()
        self.target = target
        self.radius = radius
        self.is_raw_degrees = is_raw_degrees

    def run(self):
        try:
            cadc = Cadc()

            coords = None
            if self.is_raw_degrees:
                # User claims input is RA DEC in degrees
                # (e.g. "240.5 -30.2" or "240.5, -30.2")
                # Clean split
                parts = self.target.replace(",", " ").split()
                if len(parts) >= 2:
                    try:
                        coords = SkyCoord(parts[0], parts[1], unit="deg")
                    except Exception as e:
                        self.error_occurred.emit(f"Degree parsing failed: {e}")
                        return
                else:
                    self.error_occurred.emit(
                        "Invalid degree format. Use: RA DEC (e.g., 240.5 -30.2)"
                    )
                    return
            else:
                # Standard auto-parsing
                try:
                    coords = SkyCoord(self.target)
                except Exception:
                    coords = None

            if coords is not None:
                # It's a coordinate
                result = cadc.query_region(
                    coords, radius=self.radius * u.deg, collection="NEOSSAT"
                )
            else:
                # Treat as object name
                result = cadc.query_region(
                    self.target, radius=self.radius * u.deg, collection="NEOSSAT"
                )

            if len(result) == 0 and not self.is_raw_degrees and coords is None:
                # Try explicit name query if region failed and it wasn't a coordinate
                result = cadc.query_name(self.target)
                if result is not None:
                    result = result[result["collection"] == "NEOSSAT"]

            if result is None or len(result) == 0:
                self.error_occurred.emit(f"No NEOSSAT data found for '{self.target}'")
                return

            if "intent" in result.colnames:
                science_rows = result[result["intent"] == "science"]
                if len(science_rows) > 0:
                    result = science_rows

            # Get URLs - get_data_urls returns a list of URLs corresponding to the rows
            urls = cadc.get_data_urls(result)

            if not urls:
                self.error_occurred.emit("Found metadata but no download URLs.")
                return

            # Package results
            output_list = []
            for i, row in enumerate(result):
                url = urls[i]
                obs_id = (
                    str(row["observationID"])
                    if "observationID" in row.colnames
                    else f"img{i}"
                )
                time_obs = (
                    str(row["time_observation"])
                    if "time_observation" in row.colnames
                    else "N/A"
                )

                output_list.append(
                    {
                        "url": url,
                        "obs_id": obs_id,
                        "time": time_obs,
                        "target": self.target,
                        "row_idx": i,
                    }
                )

            self.results_found.emit(output_list, result)

        except Exception as e:
            self.error_occurred.emit(f"CADC Error: {str(e)}")


class CadcDownloadThread(QThread):
    """Downloads a list of files"""

    progress_update = pyqtSignal(int, int)  # current, total
    log_msg = pyqtSignal(str)
    finished_all = pyqtSignal(int)

    def __init__(self, download_list, data_folder):
        super().__init__()
        self.download_list = download_list
        self.data_folder = data_folder
        self.is_running = True

    def run(self):
        count = 0
        total = len(self.download_list)

        # Group by target to ensure folder existence
        # But here logic passes target in each item
        for i, item in enumerate(self.download_list):
            if not self.is_running:
                break

            try:
                url = item["url"]
                target = item["target"]
                obs_id = item["obs_id"]

                safe_target_folder = "".join(
                    [c if c.isalnum() else "_" for c in target]
                )
                target_folder_path = os.path.join(self.data_folder, safe_target_folder)
                if not os.path.exists(target_folder_path):
                    os.makedirs(target_folder_path)

                filename = f"NEOSSAT_{safe_target_folder}_{obs_id}.fits"
                filepath = os.path.join(target_folder_path, filename)

                self.log_msg.emit(f"Downloading {i+1}/{total}: {filename}...")

                response = requests.get(url, stream=True)
                response.raise_for_status()

                with open(filepath, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                count += 1
                self.progress_update.emit(count, total)

            except Exception as e:
                self.log_msg.emit(f"Error downloading {item.get('obs_id', '?')}: {e}")

        self.finished_all.emit(count)

    def stop(self):
        self.is_running = False


class NeossatFtpStructureThread(QThread):
    """Fetches Years or Days from NEOSSAT FTP"""

    years_fetched = pyqtSignal(list)
    days_fetched = pyqtSignal(list)
    images_fetched = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, mode, year=None, day=None):
        super().__init__()
        self.mode = mode  # 'years', 'days', 'images'
        self.year = year
        self.day = day
        self.ftp_host = "donnees-data.asc-csa.gc.ca"
        self.base_path = "/users/OpenData_DonneesOuvertes/pub/NEOSSAT/ASTRO/"

    def run(self):
        ftp = None
        try:
            ftp = ftplib.FTP(self.ftp_host)
            ftp.login()

            if self.mode == "years":
                ftp.cwd(self.base_path)
                items = []
                ftp.retrlines("NLST", items.append)
                years = sorted([x for x in items if x.isdigit() and len(x) == 4])
                self.years_fetched.emit(years)

            elif self.mode == "days":
                if not self.year:
                    return
                ftp.cwd(f"{self.base_path}{self.year}/")
                items = []
                ftp.retrlines("NLST", items.append)
                days = sorted([x for x in items if x.isdigit()])
                self.days_fetched.emit(days)

            elif self.mode == "images":
                if not self.year or not self.day:
                    return
                ftp.cwd(f"{self.base_path}{self.year}/{self.day}/")
                items = []
                ftp.retrlines("NLST", items.append)
                images = sorted([x for x in items if x.endswith(".fits")])
                self.images_fetched.emit(images)

        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if ftp:
                try:
                    ftp.quit()
                except Exception:
                    pass


class FtpDownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, year, day, filename, data_folder):
        super().__init__()
        self.year = year
        self.day = day
        self.filename = filename
        self.data_folder = data_folder
        self.ftp_host = "donnees-data.asc-csa.gc.ca"
        self.base_path = "/users/OpenData_DonneesOuvertes/pub/NEOSSAT/ASTRO/"

    def run(self):
        ftp = None
        try:
            ftp = ftplib.FTP(self.ftp_host)
            ftp.login()
            remote_path = f"{self.base_path}{self.year}/{self.day}/{self.filename}"
            local_path = os.path.join(self.data_folder, self.filename)

            size = ftp.size(remote_path)
            self.bytes_downloaded = 0

            def callback(data):
                f.write(data)
                self.bytes_downloaded += len(data)
                if size > 0:
                    self.progress.emit(int(self.bytes_downloaded / size * 100))

            with open(local_path, "wb") as f:
                ftp.retrbinary(f"RETR {remote_path}", callback)

            self.finished.emit(True, f"Saved to {self.filename}")

        except Exception as e:
            self.finished.emit(False, str(e))
        finally:
            if ftp:
                try:
                    ftp.quit()
                except Exception:
                    pass


# --- UI Components ---


class DownloadTab(QWidget):
    def __init__(self, data_folder):
        super().__init__()
        self.data_folder = data_folder
        self.layout = QVBoxLayout()

        self.layout.addWidget(QLabel("<h2>Download FITS Image</h2>"))

        # Source Selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(
            [
                "AstroQuery Target Search" "NEOSSAT (FTP Archive Browser)",
                "SkyView (General Survey)",
            ]
        )
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        source_layout.addWidget(self.source_combo)
        self.layout.addLayout(source_layout)

        # Stacked Widget
        self.stack = QStackedWidget()

        # Astroquery
        self.page_neossat_query = QWidget()
        self.init_neossat_query_ui()
        self.stack.addWidget(self.page_neossat_query)

        # FTP
        self.page_neossat_ftp = QWidget()
        self.init_neossat_ftp_ui()
        self.stack.addWidget(self.page_neossat_ftp)

        # SkyView
        self.page_skyview = QWidget()
        self.init_skyview_ui()
        self.stack.addWidget(self.page_skyview)

        self.layout.addWidget(self.stack)

        # Common Status
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        self.layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.status_label)

        self.layout.addStretch()
        self.setLayout(self.layout)

    def init_skyview_ui(self):
        layout = QVBoxLayout()
        group = QGroupBox("SkyView Query")
        glayout = QVBoxLayout()

        # Target
        t_layout = QHBoxLayout()
        self.sv_target = QLineEdit()
        self.sv_target.setPlaceholderText("e.g. M42, Vega")
        t_layout.addWidget(QLabel("Target:"))
        t_layout.addWidget(self.sv_target)
        glayout.addLayout(t_layout)

        # Survey
        s_layout = QHBoxLayout()
        self.sv_survey = QComboBox()
        self.sv_survey.addItems(["DSS", "SDSSg", "2MASS-J", "WISE 3.4", "NVSS"])
        s_layout.addWidget(QLabel("Survey:"))
        s_layout.addWidget(self.sv_survey)
        glayout.addLayout(s_layout)

        # Radius
        r_layout = QHBoxLayout()
        self.sv_radius = QDoubleSpinBox()
        self.sv_radius.setRange(0.01, 5.0)
        self.sv_radius.setValue(0.1)
        self.sv_radius.setSuffix(" deg")
        r_layout.addWidget(QLabel("Radius:"))
        r_layout.addWidget(self.sv_radius)
        glayout.addLayout(r_layout)

        btn = QPushButton("Query & Download")
        btn.clicked.connect(self.start_skyview_download)
        glayout.addWidget(btn)

        group.setLayout(glayout)
        layout.addWidget(group)
        layout.addStretch()
        self.page_skyview.setLayout(layout)

    def init_neossat_ftp_ui(self):
        layout = QVBoxLayout()
        group = QGroupBox("Browse NEOSSAT Archive (by Date)")
        glayout = QVBoxLayout()

        # Year
        y_layout = QHBoxLayout()
        self.neo_year_combo = QComboBox()
        self.neo_year_combo.currentIndexChanged.connect(self.load_neossat_days)
        y_layout.addWidget(QLabel("Year:"))
        y_layout.addWidget(self.neo_year_combo)
        glayout.addLayout(y_layout)

        # Day
        d_layout = QHBoxLayout()
        self.neo_day_combo = QComboBox()
        self.neo_day_combo.currentIndexChanged.connect(self.load_neossat_images)
        d_layout.addWidget(QLabel("Day of Year:"))
        d_layout.addWidget(self.neo_day_combo)
        glayout.addLayout(d_layout)

        # Image
        i_layout = QHBoxLayout()
        self.neo_image_combo = QComboBox()
        i_layout.addWidget(QLabel("Image:"))
        i_layout.addWidget(self.neo_image_combo)
        glayout.addLayout(i_layout)

        refresh = QPushButton("Refresh Years")
        refresh.clicked.connect(self.load_neossat_years)
        glayout.addWidget(refresh)

        self.ftp_dl_btn = QPushButton("Download Selected Image")
        self.ftp_dl_btn.clicked.connect(self.start_ftp_download)
        self.ftp_dl_btn.setEnabled(False)
        glayout.addWidget(self.ftp_dl_btn)

        group.setLayout(glayout)
        layout.addWidget(group)
        layout.addStretch()
        self.page_neossat_ftp.setLayout(layout)

    def init_neossat_query_ui(self):
        layout = QVBoxLayout()
        group = QGroupBox("Search NEOSSAT Data")
        glayout = QVBoxLayout()

        t_layout = QHBoxLayout()
        self.cadc_target = QLineEdit()
        self.cadc_target.setPlaceholderText("e.g. M31, 10 20 (Coords)")
        t_layout.addWidget(QLabel("Target Name/Coords:"))
        t_layout.addWidget(self.cadc_target)
        glayout.addLayout(t_layout)

        # Checkbox for explicit degree input
        self.cadc_deg_chk = QCheckBox("Input is RA, Dec (Degrees)")
        self.cadc_deg_chk.setToolTip("Check if entering raw degrees like '240.5 -30.0'")
        glayout.addWidget(self.cadc_deg_chk)

        r_layout = QHBoxLayout()
        self.cadc_radius = QDoubleSpinBox()
        self.cadc_radius.setRange(0.001, 1.0)
        self.cadc_radius.setValue(0.02)
        self.cadc_radius.setSuffix(" deg")
        r_layout.addWidget(QLabel("Search Radius:"))
        r_layout.addWidget(self.cadc_radius)
        glayout.addLayout(r_layout)

        # Remove check box and Search & Download button, replace with Search button
        self.cadc_search_btn = QPushButton("Search NEOSSAT")
        self.cadc_search_btn.clicked.connect(self.start_cadc_search)
        glayout.addWidget(self.cadc_search_btn)

        # Result List
        glayout.addWidget(QLabel("Search Results (Select to Download):"))
        self.cadc_result_list = QListWidget()
        self.cadc_result_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        glayout.addWidget(self.cadc_result_list)

        self.cadc_dl_btn = QPushButton("Download Selected")
        self.cadc_dl_btn.clicked.connect(self.start_cadc_download_selected)
        self.cadc_dl_btn.setEnabled(False)
        glayout.addWidget(self.cadc_dl_btn)

        group.setLayout(glayout)
        layout.addWidget(group)
        layout.addStretch()
        self.page_neossat_query.setLayout(layout)

    def on_source_changed(self, index):
        self.stack.setCurrentIndex(index)
        if index == 1 and self.neo_year_combo.count() == 0:
            self.load_neossat_years()

    # --- SkyView Handler ---
    def start_skyview_download(self):
        target = self.sv_target.text().strip()
        if not target:
            return
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.status_label.setText("Querying SkyView...")
        self.sv_thread = SkyViewThread(
            target,
            self.sv_survey.currentText(),
            self.sv_radius.value(),
            self.data_folder,
        )
        self.sv_thread.finished.connect(self.on_download_finished)
        self.sv_thread.start()

    # --- FTP Handlers ---
    def load_neossat_years(self):
        self.status_label.setText("Fetching years...")
        self.thread_ftp_s = NeossatFtpStructureThread("years")
        self.thread_ftp_s.years_fetched.connect(
            lambda y: self.neo_year_combo.addItems(y)
        )
        self.thread_ftp_s.start()

    def load_neossat_days(self):
        year = self.neo_year_combo.currentText()
        if not year:
            return
        self.neo_day_combo.clear()
        self.neo_image_combo.clear()
        self.thread_ftp_s = NeossatFtpStructureThread("days", year=year)
        self.thread_ftp_s.days_fetched.connect(lambda d: self.neo_day_combo.addItems(d))
        self.thread_ftp_s.start()

    def load_neossat_images(self):
        year = self.neo_year_combo.currentText()
        day = self.neo_day_combo.currentText()
        if not year or not day:
            return
        self.neo_image_combo.clear()
        self.thread_ftp_s = NeossatFtpStructureThread("images", year=year, day=day)
        self.thread_ftp_s.images_fetched.connect(self.on_ftp_images_loaded)
        self.thread_ftp_s.start()

    def on_ftp_images_loaded(self, images):
        self.neo_image_combo.addItems(images)
        self.ftp_dl_btn.setEnabled(len(images) > 0)

    def start_ftp_download(self):
        year = self.neo_year_combo.currentText()
        day = self.neo_day_combo.currentText()
        fname = self.neo_image_combo.currentText()
        if not fname:
            return

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.ftp_dl = FtpDownloadThread(year, day, fname, self.data_folder)
        self.ftp_dl.progress.connect(self.progress_bar.setValue)
        self.ftp_dl.finished.connect(self.on_download_finished)
        self.ftp_dl.start()

    # --- CADC Neossat Query Handler ---
    def start_cadc_search(self):
        target = self.cadc_target.text().strip()
        radius = self.cadc_radius.value()
        is_degree_mode = self.cadc_deg_chk.isChecked()

        if not target:
            self.status_label.setText("Please enter a target.")
            return

        self.cadc_result_list.clear()
        self.cadc_dl_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.status_label.setText("Searching CADC...")
        self.cadc_search_btn.setEnabled(False)

        self.cadc_s_thread = CadcSearchThread(target, radius, is_degree_mode)
        self.cadc_s_thread.results_found.connect(self.on_cadc_results)
        self.cadc_s_thread.error_occurred.connect(self.on_cadc_error)
        self.cadc_s_thread.start()

    def on_cadc_results(self, output_list, raw_table):
        self.cadc_search_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText(f"Found {len(output_list)} records.")

        for item in output_list:
            label = f"[{item['time']}] ObsID: {item['obs_id']}"
            w_item = QListWidgetItem(label)
            w_item.setData(Qt.ItemDataRole.UserRole, item)
            self.cadc_result_list.addItem(w_item)

        if len(output_list) > 0:
            self.cadc_dl_btn.setEnabled(True)

    def on_cadc_error(self, msg):
        self.cadc_search_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText(f"Error: {msg}")

    def start_cadc_download_selected(self):
        selected_items = self.cadc_result_list.selectedItems()
        if not selected_items:
            self.status_label.setText("No items selected.")
            return

        download_list = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]

        self.cadc_dl_btn.setEnabled(False)
        self.cadc_search_btn.setEnabled(False)
        self.progress_bar.setRange(0, len(download_list))
        self.progress_bar.setValue(0)
        self.progress_bar.show()

        self.cadc_d_thread = CadcDownloadThread(download_list, self.data_folder)
        self.cadc_d_thread.progress_update.connect(
            lambda c, t: self.progress_bar.setValue(c)
        )
        self.cadc_d_thread.log_msg.connect(lambda msg: self.status_label.setText(msg))
        self.cadc_d_thread.finished_all.connect(self.on_cadc_download_finished)
        self.cadc_d_thread.start()

    def on_cadc_download_finished(self, count):
        self.cadc_dl_btn.setEnabled(True)
        self.cadc_search_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText(f"Downloaded {count} images.")
        self.status_label.setStyleSheet("color: green")

    # --- Common ---
    def on_download_finished(self, success, message):
        # This handles SkyView/FTP single file downloads
        self.progress_bar.hide()
        if success:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: green")
        else:
            self.status_label.setText(f"Error: {message}")
            self.status_label.setStyleSheet("color: red")

    def on_cadc_finished(self, success, msg):
        # Deprecated adapter if needed, but we replaced the flows.
        pass


class VisualizeTab(QWidget):
    def __init__(self, data_folder):
        super().__init__()
        self.data_folder = data_folder
        self.project_root = Path(os.path.abspath(__file__)).parent.parent

        self.layout = QHBoxLayout(self)

        # Left side: File List
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files...")
        self.search_input.textChanged.connect(self.filter_files)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderHidden(True)
        self.file_tree.itemClicked.connect(self.on_file_select)

        self.refresh_btn = QPushButton("Rescan Directory")
        self.refresh_btn.clicked.connect(self.scan_files)

        left_layout.addWidget(QLabel("FITS Files found:"))
        left_layout.addWidget(self.search_input)
        left_layout.addWidget(self.file_tree)
        left_layout.addWidget(self.refresh_btn)

        left_widget.setMaximumWidth(300)

        self.layout.addWidget(left_widget)

        # Right side: Splitter for Plot + Metadata
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        # Image
        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        self.figure = Figure(figsize=(5, 5))
        self.canvas = FigureCanvas(self.figure)
        image_layout.addWidget(self.canvas)
        right_splitter.addWidget(image_widget)

        # Metadata
        metadata_widget = QWidget()
        metadata_layout = QVBoxLayout(metadata_widget)
        metadata_layout.addWidget(QLabel("Image Info & Metadata:"))
        self.metadata_text = QTextEdit()
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        metadata_layout.addWidget(self.metadata_text)
        right_splitter.addWidget(metadata_widget)

        # Give more weight to image (first item, index 0)
        right_splitter.setStretchFactor(0, 3)
        right_splitter.setStretchFactor(1, 1)

        self.layout.addWidget(right_splitter, stretch=1)
        self.all_files = []
        self.scan_files()

    def scan_files(self):
        self.all_files = []
        self.search_input.clear()

        exclude_dirs = {
            ".venv",
            ".git",
            "__pycache__",
            "node_modules",
            ".idea",
            ".vscode",
        }

        try:
            for path in self.project_root.rglob("*"):
                if any(part in exclude_dirs for part in path.parts):
                    continue
                if path.is_file() and path.suffix.lower() in [".fits", ".fit"]:
                    self.all_files.append(path)

            self.all_files.sort()
            self.populate_tree()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to scan directory: {e}")

    def populate_tree(self, search_term=""):
        self.file_tree.clear()
        search_term = search_term.lower()
        folders = {}

        for file_path in self.all_files:
            try:
                rel_path = file_path.relative_to(self.project_root)
                parent_dir = str(rel_path.parent)
                if parent_dir == ".":
                    parent_dir = "Root"
            except ValueError:
                parent_dir = "Other"

            if (
                search_term
                and search_term not in file_path.name.lower()
                and search_term not in parent_dir.lower()
            ):
                continue

            if parent_dir not in folders:
                folder_item = QTreeWidgetItem([parent_dir])
                self.file_tree.addTopLevelItem(folder_item)
                folder_item.setExpanded(True)
                folders[parent_dir] = folder_item

            file_item = QTreeWidgetItem([file_path.name])
            file_item.setData(0, Qt.ItemDataRole.UserRole, str(file_path))
            folders[parent_dir].addChild(file_item)

    def filter_files(self, text):
        self.populate_tree(text)

    def refresh_list(self):
        self.scan_files()

    def on_file_select(self, item, column):
        file_path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path_str:
            return  # Probably a folder

        self.display_fits(Path(file_path_str))

    def display_fits(self, file_path):
        import numpy as np
        from astropy.io import fits

        try:
            with fits.open(file_path) as hdul:
                data = None
                header = None
                for hdu in hdul:
                    if hdu.data is not None:
                        if getattr(hdu, "is_image", False) or (
                            isinstance(hdu.data, np.ndarray) and hdu.data.ndim >= 2
                        ):
                            data = hdu.data
                            header = hdu.header
                            break

                self.metadata_text.clear()
                self.figure.clear()
                ax = self.figure.add_subplot(111)

                if data is None:
                    ax.text(0.5, 0.5, "No image data found in FITS", ha="center")
                    ax.axis("off")
                    self.canvas.draw()
                    self.metadata_text.setText("No image data found.\n")
                    return

                if header is not None:
                    metadata_str = f"Image dimensions: {data.shape}\n"
                    metadata_str += f"Data type: {data.dtype}\n"
                    metadata_str += "-" * 40 + "\n"
                    metadata_str += "FITS Header Metadata:\n"
                    for key, value in header.items():
                        metadata_str += f"{key:8s} = {value}\n"
                    self.metadata_text.setText(metadata_str)

                while data.ndim > 2:
                    data = data[0]

                data = np.nan_to_num(data)
                valid_data = data[np.isfinite(data)]
                if valid_data.size > 0:
                    vmin, vmax = np.percentile(valid_data, [1, 99])
                else:
                    vmin, vmax = np.min(data), np.max(data)

                _ = ax.imshow(data, cmap="gray", vmin=vmin, vmax=vmax, origin="lower")
                ax.set_title(file_path.name)
                ax.axis("off")
                self.canvas.draw()

        except Exception as e:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f"Error loading FITS:\n{str(e)}", ha="center", wrap=True)
            ax.axis("off")
            self.canvas.draw()
            self.metadata_text.setText(f"Error loading FITS:\n{str(e)}\n")
            print(f"Error loading {file_path}: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple FITS Tool")
        self.resize(1000, 750)

        # Data directory
        project_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_folder = os.path.join(project_dir, "data")
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.download_tab = DownloadTab(self.data_folder)
        self.visualize_tab = VisualizeTab(self.data_folder)

        self.tabs.addTab(self.download_tab, "Download")
        self.tabs.addTab(self.visualize_tab, "Visualize")

        # Auto-refresh list when switching to visualize tab
        self.tabs.currentChanged.connect(self.on_tab_change)

    def on_tab_change(self, index):
        if self.tabs.widget(index) == self.visualize_tab:
            self.visualize_tab.refresh_list()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
