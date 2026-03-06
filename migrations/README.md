# Database Migrations with Alembic

This project uses **Alembic** for database schema migrations, replacing the development-only `create_all()` approach.

## Why Migrations?

✅ **Production-safe schema updates** (no data loss)  
✅ **Version control for database** (track schema changes)  
✅ **Rollback capability** (undo migrations if needed)  
✅ **Team collaboration** (everyone has same schema state)

---

## Quick Start

### 1. Generate Initial Migration

```bash
# From project root
alembic revision --autogenerate -m "initial migration"
```

This will create a migration file in `migrations/versions/` based on your current models.

### 2. Apply Migration

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base
```

### 3. Check Migration Status

```bash
# Show current migration version
alembic current

# Show migration history
alembic history
```

---

## Common Workflows

### Adding a New Model/Field

1. **Update your model** in `app/models/`
2. **Generate migration**: `alembic revision --autogenerate -m "add xyz field"`
3. **Review the generated migration** in `migrations/versions/`  
   ⚠️ **IMPORTANT**: Always review before applying!
4. **Apply**: `alembic upgrade head`

### Creating a Custom Migration

```bash
# Create empty migration template
alembic revision -m "custom migration description"

# Edit the generated file manually
# Then apply: alembic upgrade head
```

### Rolling Back a Migration

```bash
# Rollback one step
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>
```

---

## Docker Usage

When running in Docker, migrations are **NOT** automatically applied (for safety).

### Apply Migrations in Docker

```bash
# Run migrations in the API container
docker-compose exec api alembic upgrade head

# Or rebuild and run migrations
docker-compose down
docker-compose up --build -d
docker-compose exec api alembic upgrade head
```

### Auto-migrate on Startup (Optional)

To run migrations automatically when the container starts, update `Dockerfile`:

```dockerfile
# Add entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
```

Create `docker-entrypoint.sh`:
```bash
#!/bin/bash
set -e

# Run migrations
alembic upgrade head

# Start application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Best Practices

### ✅ DO
- Always review auto-generated migrations before applying
- Test migrations on a copy of production data
- Keep migrations small and focused
- Add descriptive commit messages
- Run migrations in a transaction (default for PostgreSQL)

### ❌ DON'T
- Never edit migration files after they've been applied to production
- Don't skip migrations (apply sequentially)
- Don't autogenerate in production (generate locally, commit, deploy)
- Don't delete migration files from version control

---

## Troubleshooting

### "Target database is not up to date"
```bash
# Bring database to current schema version
alembic stamp head
```

### "Can't locate revision identified by..."
```bash
# Reset alembic version table (⚠️ DANGER in production)
alembic stamp base
alembic upgrade head
```

### Migration conflicts (multiple branches)
```bash
# Show branches
alembic branches

# Merge branches
alembic merge -m "merge branches" <rev1> <rev2>
```

---

## Production Deployment Checklist

1. ✅ Generate migration locally
2. ✅ Review migration SQL
3. ✅ Test on staging database
4. ✅ Commit migration to git
5. ✅ Deploy code
6. ✅ Run migration: `alembic upgrade head`
7. ✅ Verify application works
8. ✅ Monitor for errors

---

## Reference

- **Alembic Docs**: https://alembic.sqlalchemy.org/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Migration file location**: `migrations/versions/`
- **Configuration**: `alembic.ini`
- **Environment setup**: `migrations/env.py`
