from pathlib import Path
from textwrap import dedent

from domain.models import ProjectSpec


class ProjectGenerator:
    """Generates runnable FastAPI projects with HTMX or React frontends."""

    async def generate(self, spec: ProjectSpec, output_dir: Path) -> list[Path]:
        project_root = output_dir.resolve() / spec.name
        package = spec.package_name
        files = self._backend_files(spec, package)
        files.update(self._frontend_files(spec))
        files.update(self._delivery_files(spec, package))

        written: list[Path] = []
        for relative, content in files.items():
            path = project_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(path)
        return written

    def _backend_files(self, spec: ProjectSpec, package: str) -> dict[str, str]:
        features = ", ".join(spec.features) or "core workflow"
        return {
            "pyproject.toml": dedent(
                f"""
                [project]
                name = "{package}"
                version = "0.1.0"
                requires-python = ">=3.12"
                dependencies = [
                    "fastapi>=0.115.0",
                    "uvicorn[standard]>=0.30.0",
                    "sqlalchemy[asyncio]>=2.0.30",
                    "asyncpg>=0.29.0",
                    "pydantic>=2.8.0",
                    "pydantic-settings>=2.4.0",
                    "jinja2>=3.1.4",
                    "python-multipart>=0.0.9",
                ]

                [project.optional-dependencies]
                dev = ["pytest>=8.2.0", "httpx>=0.27.0", "pytest-asyncio>=0.23.0"]

                [tool.pytest.ini_options]
                asyncio_mode = "auto"
                testpaths = ["tests"]
                """
            ).strip()
            + "\n",
            f"{package}/__init__.py": '"""Generated service package."""\n',
            f"{package}/settings.py": dedent(
                """
                from pydantic_settings import BaseSettings, SettingsConfigDict


                class Settings(BaseSettings):
                    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

                    app_name: str = "Generated FastAPI Service"
                    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/app"


                settings = Settings()
                """
            ).lstrip(),
            f"{package}/database.py": dedent(
                """
                from collections.abc import AsyncIterator

                from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
                from sqlalchemy.orm import DeclarativeBase

                from .settings import settings


                class Base(DeclarativeBase):
                    pass


                engine = create_async_engine(settings.database_url, pool_pre_ping=True)
                SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


                async def get_session() -> AsyncIterator[AsyncSession]:
                    async with SessionLocal() as session:
                        yield session
                """
            ).lstrip(),
            f"{package}/models.py": dedent(
                """
                from datetime import UTC, datetime

                from sqlalchemy import DateTime, Integer, String, Text
                from sqlalchemy.orm import Mapped, mapped_column

                from .database import Base


                class WorkItem(Base):
                    __tablename__ = "work_items"

                    id: Mapped[int] = mapped_column(Integer, primary_key=True)
                    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
                    description: Mapped[str] = mapped_column(Text, nullable=False)
                    status: Mapped[str] = mapped_column(String(30), nullable=False, default="open")
                    created_at: Mapped[datetime] = mapped_column(
                        DateTime(timezone=True),
                        default=lambda: datetime.now(UTC),
                        nullable=False,
                    )
                """
            ).lstrip(),
            f"{package}/schemas.py": dedent(
                """
                from datetime import datetime

                from pydantic import BaseModel, Field


                class WorkItemCreate(BaseModel):
                    title: str = Field(min_length=2, max_length=200)
                    description: str = Field(min_length=1, max_length=4_000)


                class WorkItemRead(BaseModel):
                    id: int
                    title: str
                    description: str
                    status: str
                    created_at: datetime
                """
            ).lstrip(),
            f"{package}/main.py": self._generated_main(spec, package, features),
            "sql/schema.sql": dedent(
                """
                CREATE TABLE IF NOT EXISTS work_items (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    status VARCHAR(30) NOT NULL DEFAULT 'open',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS ix_work_items_title ON work_items (title);
                """
            ).lstrip(),
            "tests/test_health.py": dedent(
                """
                from fastapi.testclient import TestClient

                from generated_app.main import app


                def test_health() -> None:
                    client = TestClient(app)
                    response = client.get("/health")
                    assert response.status_code == 200
                    assert response.json()["status"] == "ok"
                """
            ).lstrip().replace("generated_app", package),
        }

    def _generated_main(self, spec: ProjectSpec, package: str, features: str) -> str:
        return dedent(
            f'''
            from contextlib import asynccontextmanager
            from collections.abc import AsyncIterator

            from fastapi import Depends, FastAPI, Form, Request
            from fastapi.responses import HTMLResponse
            from fastapi.staticfiles import StaticFiles
            from fastapi.templating import Jinja2Templates
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import AsyncSession

            from .database import Base, engine, get_session
            from .models import WorkItem
            from .schemas import WorkItemCreate, WorkItemRead
            from .settings import settings


            @asynccontextmanager
            async def lifespan(app: FastAPI) -> AsyncIterator[None]:
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
                yield


            app = FastAPI(title=settings.app_name, lifespan=lifespan)
            app.mount("/static", StaticFiles(directory="static"), name="static")
            templates = Jinja2Templates(directory="templates")


            @app.get("/health")
            async def health() -> dict[str, str]:
                return {{"status": "ok", "service": settings.app_name}}


            @app.get("/api/work-items", response_model=list[WorkItemRead])
            async def list_work_items(session: AsyncSession = Depends(get_session)) -> list[WorkItem]:
                rows = await session.scalars(select(WorkItem).order_by(WorkItem.created_at.desc()))
                return list(rows)


            @app.post("/api/work-items", response_model=WorkItemRead, status_code=201)
            async def create_work_item(
                payload: WorkItemCreate,
                session: AsyncSession = Depends(get_session),
            ) -> WorkItem:
                item = WorkItem(title=payload.title, description=payload.description)
                session.add(item)
                await session.commit()
                await session.refresh(item)
                return item


            @app.get("/", response_class=HTMLResponse)
            async def dashboard(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
                rows = await list_work_items(session)
                return templates.TemplateResponse("index.html", {{"request": request, "items": rows}})


            @app.post("/work-items", response_class=HTMLResponse)
            async def create_work_item_form(
                title: str = Form(...),
                description: str = Form(...),
                session: AsyncSession = Depends(get_session),
            ) -> HTMLResponse:
                await create_work_item(WorkItemCreate(title=title, description=description), session)
                rows = await list_work_items(session)
                body = "".join(f"<li><strong>{{item.title}}</strong><span>{{item.status}}</span></li>" for item in rows)
                return HTMLResponse(body)


            PROJECT_SUMMARY = {spec.summary!r}
            INITIAL_FEATURE_FOCUS = {features!r}
            '''
        ).lstrip()

    def _frontend_files(self, spec: ProjectSpec) -> dict[str, str]:
        if spec.frontend == "react":
            files = self._htmx_frontend_files(spec)
            files.update(self._react_frontend_files(spec))
            return files
        return self._htmx_frontend_files(spec)

    def _htmx_frontend_files(self, spec: ProjectSpec) -> dict[str, str]:
        return {
            "templates/index.html": dedent(
                f"""
                <!doctype html>
                <html lang="en">
                <head>
                  <meta charset="utf-8">
                  <meta name="viewport" content="width=device-width, initial-scale=1">
                  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
                  <link rel="stylesheet" href="/static/app.css">
                  <title>{spec.name}</title>
                </head>
                <body>
                  <main>
                    <h1>{spec.name}</h1>
                    <p>{spec.summary}</p>
                    <form hx-post="/work-items" hx-target="#items" hx-swap="innerHTML">
                      <label>Title <input required name="title" minlength="2" maxlength="200"></label>
                      <label>Description <textarea required name="description" rows="4"></textarea></label>
                      <button type="submit">Create</button>
                    </form>
                    <ul id="items">
                      {{% for item in items %}}
                      <li><strong>{{{{ item.title }}}}</strong><span>{{{{ item.status }}}}</span></li>
                      {{% endfor %}}
                    </ul>
                  </main>
                </body>
                </html>
                """
            ).lstrip(),
            "static/app.css": dedent(
                """
                :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, Arial; }
                body { margin: 0; background: #f7f9fb; color: #14213d; }
                main { width: min(960px, calc(100% - 32px)); margin: 48px auto; }
                form { display: grid; gap: 12px; max-width: 620px; }
                input, textarea, button { font: inherit; padding: 10px 12px; border-radius: 8px; border: 1px solid #9aa4b2; }
                button { width: fit-content; background: #0f766e; color: white; border-color: #0f766e; cursor: pointer; }
                ul { padding: 0; display: grid; gap: 10px; }
                li { list-style: none; display: flex; justify-content: space-between; padding: 12px; border: 1px solid #d7dde5; border-radius: 8px; background: white; }
                """
            ).lstrip(),
        }

    def _react_frontend_files(self, spec: ProjectSpec) -> dict[str, str]:
        return {
            "frontend/package.json": dedent(
                f"""
                {{
                  "name": "{spec.package_name}-frontend",
                  "version": "0.1.0",
                  "type": "module",
                  "scripts": {{
                    "dev": "vite --host 0.0.0.0",
                    "build": "vite build",
                    "preview": "vite preview --host 0.0.0.0"
                  }},
                  "dependencies": {{
                    "@vitejs/plugin-react": "^4.3.1",
                    "vite": "^5.4.0",
                    "react": "^18.3.1",
                    "react-dom": "^18.3.1"
                  }},
                  "devDependencies": {{}}
                }}
                """
            ).strip()
            + "\n",
            "frontend/index.html": '<div id="root"></div><script type="module" src="/src/App.jsx"></script>\n',
            "frontend/src/App.jsx": self._react_app(spec),
            "frontend/src/style.css": (
                "body{font-family:Inter,system-ui,Arial;margin:0;background:#f7f9fb;color:#14213d}"
                "main{width:min(960px,calc(100% - 32px));margin:48px auto}"
                "form{display:grid;gap:12px;max-width:620px}"
                "input,textarea,button{font:inherit;padding:10px 12px;border-radius:8px;border:1px solid #9aa4b2}"
                "button{width:fit-content;background:#0f766e;color:white;border-color:#0f766e}"
                "li{list-style:none;display:flex;justify-content:space-between;padding:12px;margin:10px 0;"
                "border:1px solid #d7dde5;border-radius:8px;background:white}\n"
            ),
        }

    def _react_app(self, spec: ProjectSpec) -> str:
        return dedent(
            f"""
            import {{ useEffect, useState }} from 'react';
            import {{ createRoot }} from 'react-dom/client';
            import './style.css';

            function App() {{
              const [items, setItems] = useState([]);
              const [form, setForm] = useState({{ title: '', description: '' }});

              useEffect(() => {{
                fetch('/api/work-items').then((response) => response.json()).then(setItems);
              }}, []);

              async function submit(event) {{
                event.preventDefault();
                const response = await fetch('/api/work-items', {{
                  method: 'POST',
                  headers: {{ 'Content-Type': 'application/json' }},
                  body: JSON.stringify(form)
                }});
                const created = await response.json();
                setItems([created, ...items]);
                setForm({{ title: '', description: '' }});
              }}

              return (
                <main>
                  <h1>{spec.name}</h1>
                  <p>{spec.summary}</p>
                  <form onSubmit={{submit}}>
                    <input value={{form.title}} onChange={{event => setForm({{...form, title: event.target.value}})}} aria-label="Title" required />
                    <textarea value={{form.description}} onChange={{event => setForm({{...form, description: event.target.value}})}} aria-label="Description" required />
                    <button>Create</button>
                  </form>
                  <ul>{{items.map((item) => <li key={{item.id}}><strong>{{item.title}}</strong><span>{{item.status}}</span></li>)}}</ul>
                </main>
              );
            }}

            createRoot(document.getElementById('root')).render(<App />);
            """
        ).lstrip()

    def _delivery_files(self, spec: ProjectSpec, package: str) -> dict[str, str]:
        return {
            "Dockerfile": dedent(
                f"""
                FROM python:3.12-slim

                ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
                WORKDIR /app
                RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
                COPY pyproject.toml ./
                RUN pip install --no-cache-dir .
                COPY . .
                EXPOSE 8000
                CMD ["uvicorn", "{package}.main:app", "--host", "0.0.0.0", "--port", "8000"]
                """
            ).lstrip(),
            "docker-compose.yml": self._compose_yaml(),
            "k8s/deployment.yaml": self._k8s_deployment(spec),
            "README.md": dedent(
                f"""
                # {spec.name}

                {spec.summary}

                ## Run locally

                ```bash
                docker compose up --build
                ```

                Open http://localhost:8000 and create a work item.

                ## API

                ```bash
                curl http://localhost:8000/health
                curl http://localhost:8000/api/work-items
                ```
                """
            ).lstrip(),
        }

    def _compose_yaml(self) -> str:
        return dedent(
            """
            services:
              app:
                build: .
                ports:
                  - "8000:8000"
                environment:
                  DATABASE_URL: postgresql+asyncpg://app:app@postgres:5432/app
                depends_on:
                  postgres:
                    condition: service_healthy
              postgres:
                image: postgres:16-alpine
                environment:
                  POSTGRES_USER: app
                  POSTGRES_PASSWORD: app
                  POSTGRES_DB: app
                healthcheck:
                  test: ["CMD-SHELL", "pg_isready -U app -d app"]
                  interval: 5s
                  timeout: 5s
                  retries: 12
                volumes:
                  - postgres_data:/var/lib/postgresql/data
            volumes:
              postgres_data:
            """
        ).lstrip()

    def _k8s_deployment(self, spec: ProjectSpec) -> str:
        return dedent(
            f"""
            apiVersion: apps/v1
            kind: Deployment
            metadata:
              name: {spec.name}
              labels:
                app: {spec.name}
            spec:
              replicas: 2
              selector:
                matchLabels:
                  app: {spec.name}
              template:
                metadata:
                  labels:
                    app: {spec.name}
                spec:
                  containers:
                    - name: api
                      image: {spec.name}:latest
                      imagePullPolicy: IfNotPresent
                      ports:
                        - containerPort: 8000
                      readinessProbe:
                        httpGet:
                          path: /health
                          port: 8000
                        periodSeconds: 10
            ---
            apiVersion: v1
            kind: Service
            metadata:
              name: {spec.name}
            spec:
              selector:
                app: {spec.name}
              ports:
                - port: 80
                  targetPort: 8000
            """
        ).lstrip()
