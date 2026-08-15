status: Mapped[str] = mapped_column(
        String(32), default="uploaded", nullable=False
    )
    # Доп. параметры видео. Название extra_metadata — т.к. "metadata"
    # зарезервировано в Declarative API SQLAlchemy.
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)