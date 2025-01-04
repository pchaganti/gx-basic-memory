from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class SearchQuery(BaseModel):
    text: str
    types: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None
    after_date: Optional[datetime] = None

class SearchResult(BaseModel):
    path_id: str
    file_path: str
    type: str
    score: float
    metadata: dict