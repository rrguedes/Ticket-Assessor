"""
SQLAlchemy ORM models.
Single Responsibility: Only defines the database schema.
"""
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database.connection import Base


class TicketEvaluation(Base):
    __tablename__ = "ticket_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(100), nullable=False, index=True)
    ticket_title = Column(Text, nullable=True)
    ticket_description = Column(Text, nullable=True)
    ticket_type = Column(String(50), nullable=True)
    ticket_state = Column(String(50), nullable=True)
    score = Column(Float, nullable=False)
    feedback = Column(Text, nullable=False)
    strengths = Column(JSON, nullable=True, default=list)
    additional_questions = Column(JSON, nullable=True, default=list)
    evaluated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
