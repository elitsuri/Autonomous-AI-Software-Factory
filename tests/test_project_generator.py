from pathlib import Path

import pytest

from domain.models import ProjectSpec
from services.project_generator import ProjectGenerator


@pytest.mark.asyncio
async def test_project_generator_writes_backend_frontend_schema_and_delivery_files(tmp_path: Path) -> None:
    spec = ProjectSpec(
        name="inventory-hub",
        summary="Inventory coordination service for warehouse operators.",
        frontend="react",
        features=["work items", "operator view"],
    )

    written = await ProjectGenerator().generate(spec, tmp_path)
    root = tmp_path / spec.name
    relative = {path.relative_to(root).as_posix() for path in written}

    assert "inventory_hub/main.py" in relative
    assert "templates/index.html" in relative
    assert "frontend/src/App.jsx" in relative
    assert "sql/schema.sql" in relative
    assert "Dockerfile" in relative
    assert "docker-compose.yml" in relative
    assert "k8s/deployment.yaml" in relative
    assert "CREATE TABLE IF NOT EXISTS work_items" in (root / "sql" / "schema.sql").read_text(encoding="utf-8")

