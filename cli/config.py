from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class Config:
    smtp_user: str = ""
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_password: str = ""
    send_email: bool = True
    data_dir: str = "./data"
    results_dir: str = "./results"
    reports_dir: str = "./reports"
    wrong_mode_dir: str = "./wrong_mode"


def load_config(path: Optional[str]) -> Config:
    if path is None:
        default = Path("config.yaml")
        if not default.exists():
            return Config()
        path = str(default)

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
