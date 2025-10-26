from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
import datetime
from sqlmodel import SQLModel, Field
# ---------------------------
# Score
# ---------------------------
class BaseScore(SQLModel):
    value: int

class CreateScoreRequest(BaseScore):
    pass

class UpdateScoreRequest(BaseModel):
    value: Optional[int] = None

class Score(BaseScore, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    updated_at: str = Field(default=datetime.datetime.now().strftime('%Y-%m-%d'))

class ScoreResponse(BaseModel):
    id: int
    value: int

    class Config:
        from_attributes = True