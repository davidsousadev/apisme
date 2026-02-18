from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

# ---------------------------
# Score
# ---------------------------

class BaseScore(SQLModel):
    nick: str
    value: int

class CreateScoreRequest(BaseScore):
    pass

class UpdateScoreRequest(BaseModel):
    value: Optional[int] = None

class Score(BaseScore, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # ✅ Atualização UTC timezone-aware
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ScoreResponse(BaseModel):
    id: int
    value: int
    updated_at: datetime

    class Config:
        from_attributes = True
