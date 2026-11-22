from app.routers.conjunction_events import router as conjunction_events_router
from app.routers.health import router as health_router
from app.routers.manoeuvre_plans import router as manoeuvre_plans_router
from app.routers.orbital_states import router as orbital_states_router
from app.routers.satellites import router as satellites_router
from app.routers.simulation_runs import router as simulation_runs_router
from app.routers.sustainability_metrics import router as sustainability_metrics_router

__all__ = [
    "health_router",
    "satellites_router",
    "orbital_states_router",
    "conjunction_events_router",
    "manoeuvre_plans_router",
    "simulation_runs_router",
    "sustainability_metrics_router",
]
