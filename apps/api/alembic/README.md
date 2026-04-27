# Alembic migrations

```bash
# autogenerate after model changes
uv run alembic revision --autogenerate -m "short description"

# apply
uv run alembic upgrade head

# roll back one step
uv run alembic downgrade -1
```

Never edit a merged migration. Write a follow-up instead.
