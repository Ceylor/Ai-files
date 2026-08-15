sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("extra_metadata", sa.JSON(), nullable=True),