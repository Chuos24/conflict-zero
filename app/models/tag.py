"""Tag Model - Para categorización de RUCs"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base

class Tag(Base):
    """Modelo de Tags para categorizar RUCs"""
    __tablename__ = "tags"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    color = Column(String(7), nullable=False, default="#C5A059")  # Hex color
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    user = relationship("User", back_populates="tags")
    ruc_tags = relationship("RUCTag", back_populates="tag", cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True


class RUCTag(Base):
    """Modelo de asociación entre RUCs y Tags"""
    __tablename__ = "ruc_tags"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    tag_id = Column(String(36), ForeignKey("tags.id"), nullable=False, index=True)
    ruc = Column(String(11), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    tag = relationship("Tag", back_populates="ruc_tags")
    
    __table_args__ = (
        # Unique constraint: un usuario no puede taggear el mismo RUC con el mismo tag dos veces
        # sa.UniqueConstraint('user_id', 'tag_id', 'ruc', name='uq_user_tag_ruc'),
    )
    
    class Config:
        from_attributes = True
