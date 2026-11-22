from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers.conjunction_events import router as conjunction_events_router
from app.routers.health import router as health_router
from app.routers.manoeuvre_plans import router as manoeuvre_plans_router
from app.routers.orbital_states import router as orbital_states_router
from app.routers.satellites import router as satellites_router
from app.routers.simulation_runs import router as simulation_runs_router
from app.routers.sustainability_metrics import router as sustainability_metrics_router
from app.routers.coordination import router as coordination_router
from app.routers.orbital import router as orbital_router

app = FastAPI(
    title="ORBI-SYNC API",
    description=(
        "Backend API for ORBI-SYNC Satellite Collision Avoidance System. "
        "Manages satellite catalogs, orbital states, conjunction predictions, manoeuvre plans, simulation runs, and space sustainability metrics via Supabase PostgreSQL."
    ),
    version="0.8.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS) for local frontend development and external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex if settings.cors_origin_regex else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular routers
app.include_router(health_router)
app.include_router(satellites_router)
app.include_router(orbital_states_router)
app.include_router(conjunction_events_router)
app.include_router(manoeuvre_plans_router)
app.include_router(simulation_runs_router)
app.include_router(sustainability_metrics_router)
app.include_router(coordination_router)
app.include_router(orbital_router)
