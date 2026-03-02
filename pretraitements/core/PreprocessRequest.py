from typing import List
from pydantic import BaseModel


class PreprocessRequest(BaseModel):
    fits_file: str
    preprocessors: List[str]
