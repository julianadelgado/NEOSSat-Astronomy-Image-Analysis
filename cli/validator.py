import os

import typer


def validate_data_directory(value: str) -> str:
    if value and not os.path.exists(value):
        raise typer.BadParameter(f"'{value}' is not a valid directory.")
    return value


def validate_email(value: str) -> str:
    if value and ("@" not in value or "." not in value):
        raise typer.BadParameter(f"'{value}' is not a valid email address.")
    return value
