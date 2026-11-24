"""SQLAlchemy ORM models — the Digital Crop Twin.

Enum-like columns are stored as strings (portable, migration-friendly); the allowed values are
documented in app/models/enums.py and validated at the API/schema layer.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.db import Base

EMBED_DIM = 1024

# Embeddings need pgvector, which only exists on Postgres. On SQLite we store the vector as JSON
# so the schema still creates and every non-RAG feature works. Nothing reads this column yet —
# when RAG is built it will run on Postgres, where the real vector type is used.
if settings.database_url.startswith("sqlite"):
    EmbeddingColumn = JSON
else:  # pragma: no cover - exercised only against Postgres
    from pgvector.sqlalchemy import Vector

    EmbeddingColumn = Vector(EMBED_DIM)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Farmer(Base):
    __tablename__ = "farmers"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    # The anonymous per-install id the app generated BEFORE anyone logged in. Linking it here is
    # what lets a farmer's pre-login photo captures be attributed to them afterwards instead of
    # being stranded (see docs/DATASET.md — the split group has to stay intact).
    device_id: Mapped[str | None] = mapped_column(String(64), index=True)
    preferred_lang: Mapped[str] = mapped_column(String(2), default="mr")  # mr|hi|en
    village: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    farms: Mapped[list[Farm]] = relationship(back_populates="farmer")


class Farm(Base):
    __tablename__ = "farms"
    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    area_acres: Mapped[float | None] = mapped_column(Float)
    # Asked once here, then reused by weather, irrigation and mandi prices. Before this they were
    # re-asked on every screen, which is the fastest way to lose a farmer on a cheap phone.
    district: Mapped[str | None] = mapped_column(String(64))
    soil: Mapped[str | None] = mapped_column(String(16))              # heavy|medium|light
    irrigation_method: Mapped[str | None] = mapped_column(String(16)) # drip|sprinkler|flood
    row_spacing_m: Mapped[float | None] = mapped_column(Float)
    plant_spacing_m: Mapped[float | None] = mapped_column(Float)
    emitter_lph: Mapped[float | None] = mapped_column(Float)
    emitters_per_plant: Mapped[int | None] = mapped_column(Integer)

    farmer: Mapped[Farmer] = relationship(back_populates="farms")
    crop_cycles: Mapped[list[CropCycle]] = relationship(back_populates="farm")


class CropCycle(Base):
    """One planting of one crop on one farm — the unit of the Twin."""
    __tablename__ = "crop_cycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    crop: Mapped[str] = mapped_column(String(20))  # onion|soybean|pomegranate
    variety: Mapped[str | None] = mapped_column(String(80))
    sowing_date: Mapped[date | None] = mapped_column(Date)
    expected_harvest: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|harvested|abandoned
    current_health_score: Mapped[int | None] = mapped_column(Integer)
    # Set by the "आज पाणी दिले" button; the irrigation plan reads it instead of asking again.
    last_watered_date: Mapped[date | None] = mapped_column(Date)
    harvest_date: Mapped[date | None] = mapped_column(Date)
    yield_quintal: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    farm: Mapped[Farm] = relationship(back_populates="crop_cycles")
    events: Mapped[list[CropEvent]] = relationship(back_populates="crop_cycle")


class CropEvent(Base):
    """Anything that happens on a cycle's timeline (image, voice, diagnosis, treatment, note)."""
    __tablename__ = "crop_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_cycle_id: Mapped[int] = mapped_column(ForeignKey("crop_cycles.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))  # see enums.EVENT_TYPES
    day_index: Mapped[int | None] = mapped_column(Integer)  # days since sowing
    title: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    # Structured detail (severity, disease slug, mm applied...) so the timeline and the health
    # score read one shape rather than re-querying four tables.
    data: Mapped[dict | None] = mapped_column(JSON)
    # Set when the event came from a /vision/diagnose call, so a photo on the timeline links
    # back to the captured image and its prediction.
    diagnosis_id: Mapped[str | None] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    crop_cycle: Mapped[CropCycle] = relationship(back_populates="events")
    images: Mapped[list[Image]] = relationship(back_populates="event")


class Image(Base):
    __tablename__ = "images"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_event_id: Mapped[int] = mapped_column(ForeignKey("crop_events.id"), index=True)
    s3_key: Mapped[str] = mapped_column(String(255))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    event: Mapped[CropEvent] = relationship(back_populates="images")


class Diagnosis(Base):
    __tablename__ = "diagnoses"
    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), index=True)
    crop: Mapped[str] = mapped_column(String(20))
    disease: Mapped[str] = mapped_column(String(120))
    confidence: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(50), default="mock-0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SeverityAssessment(Base):
    __tablename__ = "severity_assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    diagnosis_id: Mapped[int] = mapped_column(ForeignKey("diagnoses.id"), index=True)
    level: Mapped[str] = mapped_column(String(20))  # healthy|mild|moderate|severe|critical
    severity_pct: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    method: Mapped[str] = mapped_column(String(20), default="llm")  # llm|segmentation
    model_version: Mapped[str] = mapped_column(String(50), default="mock-0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_cycle_id: Mapped[int] = mapped_column(ForeignKey("crop_cycles.id"), index=True)
    diagnosis_id: Mapped[int | None] = mapped_column(ForeignKey("diagnoses.id"))
    treatment_plan: Mapped[dict | None] = mapped_column(JSON)
    spray: Mapped[dict | None] = mapped_column(JSON)
    prevention: Mapped[dict | None] = mapped_column(JSON)
    followup_date: Mapped[date | None] = mapped_column(Date)
    source_citations: Mapped[dict | None] = mapped_column(JSON)
    lang: Mapped[str] = mapped_column(String(2), default="mr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class HealthScore(Base):
    __tablename__ = "health_scores"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_cycle_id: Mapped[int] = mapped_column(ForeignKey("crop_cycles.id"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    breakdown: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), index=True)
    crop_cycle_id: Mapped[int | None] = mapped_column(ForeignKey("crop_cycles.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    messages: Mapped[list[Message]] = relationship(back_populates="conversation")


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user|assistant
    text: Mapped[str] = mapped_column(Text)
    audio_s3_key: Mapped[str | None] = mapped_column(String(255))
    lang: Mapped[str] = mapped_column(String(2), default="mr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class KbDocument(Base):
    __tablename__ = "kb_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str | None] = mapped_column(String(120))
    crop: Mapped[str | None] = mapped_column(String(20))
    title: Mapped[str | None] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    chunks: Mapped[list[KbChunk]] = relationship(back_populates="document")


class KbChunk(Base):
    __tablename__ = "kb_chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    kb_document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingColumn)

    document: Mapped[KbDocument] = relationship(back_populates="chunks")


class ExpertLabel(Base):
    """The data moat: human-verified disease + severity labels."""
    __tablename__ = "expert_labels"
    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), index=True)
    labeler_id: Mapped[str | None] = mapped_column(String(80))
    disease: Mapped[str | None] = mapped_column(String(120))
    severity_level: Mapped[str | None] = mapped_column(String(20))
    severity_pct: Mapped[float | None] = mapped_column(Float)
    bbox_or_mask: Mapped[dict | None] = mapped_column(JSON)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
