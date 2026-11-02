set dotenv-load

default:
    @just --list

# Install all dependencies (Python, web, iOS project generation)
setup:
    uv sync --all-packages
    pnpm install
    cd apps/ios && xcodegen generate

# Start Postgres (TimescaleDB + pgvector)
db:
    docker compose -f deploy/compose.yaml up -d db

# Apply database migrations
migrate:
    cd apps/server && uv run alembic upgrade head

# Create a new migration from model changes
migration name:
    cd apps/server && uv run alembic revision --autogenerate -m "{{name}}"

# Run the API + MCP server with reload
server:
    uv run uvicorn resident_server.main:asgi --reload --port 8000

# Pair a device and print its token, e.g. `just device-add iphone ingest`
device-add name +scopes:
    uv run resident devices add {{name}} {{prepend("--scope ", scopes)}}

# List paired devices
devices:
    uv run resident devices list

# Revoke a device's token
device-revoke name:
    uv run resident devices revoke {{name}}

# Run the web dashboard dev server
web:
    pnpm --filter @resident/web dev

# Export the OpenAPI spec and regenerate the TypeScript client
openapi:
    uv run python -m resident_server.export_openapi openapi/openapi.json
    pnpm --filter @resident/web exec openapi-typescript ../../openapi/openapi.json -o src/api/schema.d.ts

# Run all tests
test:
    uv run pytest
    pnpm --filter @resident/web test

# Lint and format check
lint:
    uv run ruff check .
    uv run ruff format --check .
    pnpm --filter @resident/web lint

# Generate the Xcode project and open it
ios:
    cd apps/ios && xcodegen generate && open Resident.xcodeproj
