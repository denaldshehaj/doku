"""Pydantic request/response models for the DOKU API.

Mirrors the shapes the core modules already produce (rag_pipeline.Answer,
SQLite rows) so the API layer stays a pure translation, not a redesign.
"""
from pydantic import BaseModel, Field

# --- Auth -------------------------------------------------------------------


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordIn(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    must_change_password: bool


# --- Chat / RAG ---------------------------------------------------------------


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_id: int | None = None       # restrict search to one document
    doc_type: str | None = None          # or filter the active corpus
    institution: str | None = None
    year: int | None = None
    title_kw: str | None = None


class SourceOut(BaseModel):
    n: int
    filename: str
    title: str
    document_type: str
    institution: str
    page: int
    score: float
    fragment: str


class AnswerOut(BaseModel):
    row_id: int
    text: str
    refused: bool
    sources: list[SourceOut]
    top_score: float
    response_time: float
    chunks_used: int
    min_similarity: float


# --- Summaries ----------------------------------------------------------------


class SummarizeIn(BaseModel):
    document_id: int
    format: str = "E shkurtër"


class SummaryOut(BaseModel):
    document_id: int
    title: str
    filename: str
    format: str
    summary: str


class SummaryExportIn(BaseModel):
    document_id: int
    format: str
    summary: str


# --- Documents ------------------------------------------------------------------


class DocumentOut(BaseModel):
    id: int
    filename: str
    original_filename: str | None
    title: str | None
    institution: str | None
    document_type: str | None
    year: int | None
    description: str | None
    uploaded_by: str | None
    status: str
    num_pages: int
    total_chunks: int
    created_at: str
    updated_at: str


class DocumentPatchIn(BaseModel):
    title: str | None = None
    institution: str | None = None
    document_type: str | None = None
    year: int | None = None
    description: str | None = None


class StatusIn(BaseModel):
    status: str  # active | inactive


# --- Users (admin) ---------------------------------------------------------------


class UserCreateIn(BaseModel):
    username: str
    password: str
    full_name: str = ""
    department: str = ""
    role: str


class UserPatchIn(BaseModel):
    full_name: str | None = None
    department: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserRowOut(BaseModel):
    id: int
    username: str
    full_name: str
    department: str
    role: str
    is_active: bool
    created_at: str


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=6, max_length=128)
    must_change: bool = True


# --- History / audit ---------------------------------------------------------------


class HistoryRowOut(BaseModel):
    id: int
    question: str
    answer: str | None
    mode: str
    selected_document_id: int | None
    sources: list[SourceOut]
    response_time: float | None
    exported_to_word: bool
    created_at: str


class AuditRowOut(BaseModel):
    username: str | None
    action: str
    details: str | None
    created_at: str


# --- Experiments -------------------------------------------------------------------


class ExperimentRunIn(BaseModel):
    questions: list[str] = Field(min_length=1)


class ExperimentPatchIn(BaseModel):
    manual_accuracy_without_rag: int | None = Field(default=None, ge=1, le=5)
    manual_accuracy_with_rag: int | None = Field(default=None, ge=1, le=5)
    hallucination_without_rag: str | None = None
    hallucination_with_rag: str | None = None
    notes: str | None = None


class ExperimentRowOut(BaseModel):
    id: int
    question: str
    answer_without_rag: str | None
    answer_with_rag: str | None
    time_without_rag: float | None
    time_with_rag: float | None
    chunks_used: int | None
    has_sources: bool
    manual_accuracy_without_rag: int | None
    manual_accuracy_with_rag: int | None
    hallucination_without_rag: str | None
    hallucination_with_rag: str | None
    notes: str | None
    created_at: str


# --- System / tasks -----------------------------------------------------------------


class ModelIn(BaseModel):
    model: str


class TaskOut(BaseModel):
    id: str
    name: str
    status: str          # running | done | error
    progress: float      # 0..1
    message: str
    result: dict | None
    error: str | None
