# backend/models.py
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class Execution(Base):
    __tablename__ = "executions"

    # We will use the UUID you generated as the primary key
    id = Column(String, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    generated_code = Column(Text, nullable=False)
    status = Column(String, nullable=False) # e.g., "success" or "error"
    output_logs = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Link to artifacts
    artifacts = relationship("Artifact", back_populates="execution")

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, ForeignKey("executions.id"))
    filename = Column(String, nullable=False)
    
    # Link back to execution
    execution = relationship("Execution", back_populates="artifacts")