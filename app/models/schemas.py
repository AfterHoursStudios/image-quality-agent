from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ScoreDetail(BaseModel):
    score: int = Field(..., ge=1, le=100, description="Score from 1-100")
    explanation: str = Field(..., description="Brief explanation of the score")


class ImageScores(BaseModel):
    sharpness: ScoreDetail = Field(..., description="Focus and clarity of the image")
    lighting: ScoreDetail = Field(..., description="Quality and balance of lighting")
    composition: ScoreDetail = Field(..., description="Framing, rule of thirds, balance")
    color: ScoreDetail = Field(..., description="Color accuracy, white balance, saturation")
    exposure: ScoreDetail = Field(..., description="Proper exposure, highlights and shadows")
    faces: Optional[ScoreDetail] = Field(None, description="Face quality if present, null if no faces")
    overall: ScoreDetail = Field(..., description="Weighted average of all applicable scores")


class ImageResponse(BaseModel):
    id: str = Field(..., description="Unique image identifier")
    url: str = Field(..., description="Public URL of the image")
    filename: str = Field(..., description="Original filename")
    scores: ImageScores = Field(..., description="All quality scores")
    created_at: datetime = Field(..., description="Analysis timestamp")


class ImageListItem(BaseModel):
    id: str
    url: str
    filename: str
    overall_score: int
    created_at: datetime


class ImageListResponse(BaseModel):
    images: list[ImageListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
