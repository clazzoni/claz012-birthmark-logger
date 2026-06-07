from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MapRegion = Literal[
    "face",
    "front_torso",
    "back",
    "left_arm",
    "right_arm",
    "left_leg",
    "right_leg",
    "left_hand",
    "right_hand",
]


class MarkCreate(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    body_region: str | None = None
    notes: str | None = None


class MarkUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    body_region: str | None = None
    notes: str | None = None


class MarkPlacement(BaseModel):
    map_region: MapRegion
    map_x: float = Field(ge=0.0, le=1.0)
    map_y: float = Field(ge=0.0, le=1.0)


class Mark(BaseModel):
    id: str
    label: str
    body_region: str | None = None
    notes: str | None = None
    created_at: datetime
    capture_count: int = 0
    last_capture_at: datetime | None = None
    map_region: str | None = None
    map_x: float | None = None
    map_y: float | None = None

    @property
    def is_placed(self) -> bool:
        return (
            self.map_region is not None
            and self.map_x is not None
            and self.map_y is not None
        )


class Capture(BaseModel):
    id: int
    mark_id: str
    captured_at: datetime
    file_path: str
    file_hash: str | None = None
    imported_at: datetime
    original_filename: str | None = None


class CapturePreview(BaseModel):
    temp_id: str
    original_filename: str
    captured_at: datetime
    exif_found: bool
    warning: str | None = None


class ImportConfirmItem(BaseModel):
    temp_id: str
    captured_at: datetime
