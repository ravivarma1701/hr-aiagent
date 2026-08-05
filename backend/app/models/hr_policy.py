from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HRPolicy(Base):
    __tablename__ = "hr_policies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(220), index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    # Phase-3 placeholder for vector search; embeddings remain empty until Phase-4.
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
