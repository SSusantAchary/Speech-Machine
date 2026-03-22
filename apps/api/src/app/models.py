from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    mode = Column(String(80), nullable=True)
    prompt = Column(Text, nullable=True)
    goal = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0)
    wpm_avg = Column(Float, default=0)
    filler_count = Column(Integer, default=0)
    eye_contact_pct = Column(Float, default=0)
    video_path = Column(String(1024), nullable=True)
    document_path = Column(String(1024), nullable=True)
    document_name = Column(String(255), nullable=True)
    document_mime_type = Column(String(255), nullable=True)
    document_blocks_json = Column(Text, nullable=True)
    transcription_status = Column(String(32), default="idle")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    transcript_segments = relationship(
        "TranscriptSegment", back_populates="session", cascade="all, delete-orphan"
    )
    metrics = relationship(
        "MetricsTimeseries", back_populates="session", cascade="all, delete-orphan"
    )
    score = relationship("Score", back_populates="session", uselist=False, cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="session", cascade="all, delete-orphan")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)

    session = relationship("Session", back_populates="transcript_segments")


class MetricsTimeseries(Base):
    __tablename__ = "metrics_timeseries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    t = Column(Integer, nullable=False)
    wpm = Column(Float, default=0)
    rms = Column(Float, default=0)
    eye_contact = Column(Float, default=0)
    smile = Column(Float, default=0)
    yaw = Column(Float, default=0)
    pitch = Column(Float, default=0)
    roll = Column(Float, default=0)
    filler_count = Column(Integer, default=0)
    pause_ms = Column(Integer, default=0)

    session = relationship("Session", back_populates="metrics")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    data = Column(JSON, nullable=False)

    session = relationship("Session", back_populates="score")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    name = Column(String(80), nullable=False)

    session = relationship("Session", back_populates="tags")
