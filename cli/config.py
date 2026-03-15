from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Config:
    email: str = ""
    data_dir: str = ""
    output_dir: str = "./output"


def load_config(path: str | None) -> Config:
    if path is None:
        default = Path("config.yaml")
        if not default.exists():
            return Config()
        path = str(default)

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
