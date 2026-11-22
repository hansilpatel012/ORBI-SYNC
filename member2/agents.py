"""Satellite agent model: constraints only, no real spacecraft control."""

from dataclasses import dataclass, field


@dataclass
class SatelliteAgent:
    object_id: str
    can_manoeuvre: bool
    fuel_budget_ms: float
    mission_rules: dict = field(default_factory=dict)

    def can_accept_manoeuvre(self, dv_ms: float, orbit_change_km: float = 0.0) -> bool:
        if not self.can_manoeuvre or dv_ms < 0:
            return False
        if dv_ms > self.fuel_budget_ms:
            return False

        max_dv = self.mission_rules.get("max_dv_ms")
        if max_dv is not None and dv_ms > float(max_dv):
            return False

        max_change = self.mission_rules.get("max_orbit_change_km")
        if max_change is not None and orbit_change_km > float(max_change):
            return False

        return True

    def fuel_cost_percent(self, dv_ms: float) -> float:
        if self.fuel_budget_ms <= 0:
            return 0.0 if dv_ms == 0 else 100.0
        return 100.0 * dv_ms / self.fuel_budget_ms
