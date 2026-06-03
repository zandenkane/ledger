"""Dataclass definitions for Project, Session, and Contribution."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Project:
    """A creative project that contributions are recorded against."""

    id: int
    name: str
    medium: str
    created_at: str

    def __str__(self) -> str:
        return f"{self.name} ({self.medium})"


@dataclass
class Session:

    id: int
    project_id: int
    title: str
    location: Optional[str]
    started_at: str
    ended_at: Optional[str]
    notes: Optional[str]

    @property
    def is_open(self) -> bool:
        return self.ended_at is None

    def __str__(self) -> str:
        status = "open" if self.is_open else "closed"
        return f"Session {self.id}: {self.title} ({status})"


@dataclass
class Contribution:
    """A single entry in the hash chain recording who did what."""

    seq: int
    project_id: int
    session_id: int
    contributor: str
    role: str
    description: Optional[str]
    split_pct: Optional[float]
    timestamp: str
    prev_hash: str
    hash: str

    @property
    def short_hash(self) -> str:
        """Return the first 12 characters of the hash for display."""
        return self.hash[:12]

    def __str__(self) -> str:
        split_str = f" {self.split_pct:.1f}%" if self.split_pct is not None else ""
        return f"#{self.seq} {self.contributor} ({self.role}){split_str}"
