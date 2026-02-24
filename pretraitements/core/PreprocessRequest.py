from pydantic import BaseModel # pyright: ignore[reportMissingImports]

class PreprocessRequest(BaseModel):
    fits_file: str
    preprocessors: list[str]