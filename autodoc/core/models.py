"""Shared data models used across core, CLI and API."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DocFormat(str, Enum):
    docx = "docx"
    xlsx = "xlsx"
    pptx = "pptx"
    pdf = "pdf"
    txt = "txt"
    md = "md"


class QuestionType(str, Enum):
    fill_blank = "fill_blank"
    choice = "choice"
    short_answer = "short_answer"
    essay = "essay"
    unknown = "unknown"


class Anchor(BaseModel):
    """A format-specific pointer to where an answer must be written.

    The fields used depend on the document format. ``locator`` is an
    opaque, format-specific token produced by the parser and consumed by
    the editor, guaranteeing the editor writes to the exact location the
    parser identified (so we never create a new document).
    """

    format: DocFormat
    locator: str = Field(..., description="Opaque format-specific location token")
    page: Optional[int] = None
    detail: dict = Field(default_factory=dict)


class Question(BaseModel):
    id: str
    number: Optional[str] = None
    text: str
    qtype: QuestionType = QuestionType.unknown
    options: List[str] = Field(default_factory=list)
    anchor: Anchor


class ParseResult(BaseModel):
    path: str
    format: DocFormat
    questions: List[Question] = Field(default_factory=list)


class Answer(BaseModel):
    question_id: str
    text: str


class EditResult(BaseModel):
    path: str
    format: DocFormat
    answers_written: int
    in_place: bool = True
    mode: Optional[str] = None
