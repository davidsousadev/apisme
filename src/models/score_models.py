from typing import Optional
from pydantic import BaseModel
from datetime import datetime
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
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ScoreResponse(BaseModel):
    id: int
    value: int
    updated_at: datetime

    class Config:
        from_attributes = True
