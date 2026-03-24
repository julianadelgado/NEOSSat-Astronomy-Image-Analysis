from pydantic import BaseModel


class PreprocessRequest(BaseModel):
    fits_file: str
    preprocessors: list[str]
