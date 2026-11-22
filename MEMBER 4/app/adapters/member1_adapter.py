"""Validated adapter connecting Member 1 Orbital Engine with Member 4 FastAPI backend.

Loads and serves Member 1's actual orbital datasets:
- Conjunction screening results (conjunction.json)
- Linear TLE-age uncertainty model (uncertainty.json)
- Orbital trajectories in GCRS frame (trajectories.json with adaptive sampling)
- TLE satellite metadata and catalogue (tle_metadata.csv)

Connects Member 1 close approaches into Member 2's encounter-plane risk engine,
while clearly labeling all manoeuvre plans as synthetic until real repropagation is implemented.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Search paths for Member 1 extracted repository
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent

MEMBER1_OUTPUT_CANDIDATES = [
    WORKSPACE_ROOT / "member 1" / "ORBI-SYNC" / "member1" / "output",
    WORKSPACE_ROOT / "member1" / "output",
    WORKSPACE_ROOT / "member 1" / "member1" / "output",
]

MEMBER1_DATA_CANDIDATES = [
    WORKSPACE_ROOT / "member 1" / "ORBI-SYNC" / "data" / "processed",
    WORKSPACE_ROOT / "member1" / "data" / "processed",
    WORKSPACE_ROOT / "data" / "processed",
]

SYNTHETIC_MANOEUVRE_WARNING = (
    "SYNTHETIC TEST OUTPUT: Manoeuvre plan uses Member 2 linear approximation. "
    "Full collision avoidance flight certification requires Member 1 numerical repropagation."
)


# ==============================================================================
# Pydantic Schemas matching Member 1 Actual Contracts
# ==============================================================================

class ConjunctionMetadata(BaseModel):
    generated_at_utc: str
    screening_distance_km: float
    close_approach_threshold_km: float
    total_satellites: int
    total_timestamps: int
    candidate_pairs: int
    candidate_encounter_events: int
    close_approaches: int
    boundary_warning_events: int
    tle_sha256: str
    refinement_method: str
    note: str


class ConjunctionEventM1(BaseModel):
    norad_id_1: str
    norad_id_2: str
    satellite_1: str
    satellite_2: str
    tca_utc: str
    miss_distance_km: float
    sampled_distance_km: float
    refinement_window_seconds: float
    refinement_method: str
    refinement_boundary_warning: bool


class ConjunctionsResponse(BaseModel):
    metadata: ConjunctionMetadata
    conjunctions: List[ConjunctionEventM1]


class UncertaintyMetadata(BaseModel):
    generated_at: str
    model: str
    base_uncertainty_km: float
    growth_rate_km_per_hour: float
    total_satellites: int
    updated_conjunctions: int


class SatelliteUncertainty(BaseModel):
    name: str
    norad_id: str
    tle_age_hours: float
    uncertainty_scale_km: float


class UncertaintyResponse(BaseModel):
    metadata: UncertaintyMetadata
    satellite_uncertainties: List[SatelliteUncertainty]


class OrbitalSatellite(BaseModel):
    name: str
    norad_id: str
    line1: str
    line2: str
    epoch: str
    tle_age_hours: float


class OrbitalSatellitesResponse(BaseModel):
    total: int
    count: int
    offset: int
    limit: int
    items: List[OrbitalSatellite]


class TrajectoryMetadata(BaseModel):
    generated_at: str
    start_time_utc: str
    end_time_utc: str
    duration_days: int
    interval_seconds: int
    sample_step: int = 1
    coordinate_frame: str
    position_unit: str
    velocity_unit: str
    total_satellites: int
    failed_satellites: int
    tle_sha256: str


class SatelliteTrajectorySampled(BaseModel):
    name: str
    norad_id: str
    positions_km: List[Optional[List[float]]]
    velocities_km_s: List[Optional[List[float]]]


class TrajectoriesResponse(BaseModel):
    metadata: TrajectoryMetadata
    timestamps_utc: List[str]
    trajectories: List[SatelliteTrajectorySampled]


class DatasetFreshness(BaseModel):
    status: str
    conjunction_generated_at_utc: Optional[str] = None
    uncertainty_generated_at: Optional[str] = None
    trajectories_generated_at: Optional[str] = None
    trajectory_start_time_utc: Optional[str] = None
    trajectory_end_time_utc: Optional[str] = None
    tle_sha256: Optional[str] = None
    total_satellites: int = 0
    total_conjunctions: int = 0
    data_freshness_status: str
    note: str


# ==============================================================================
# Member 1 Storage & Adapter Loader
# ==============================================================================

class Member1Adapter:
    """Manages reading, caching, and serving Member 1 orbital datasets."""

    _output_dir: Optional[Path] = None
    _data_dir: Optional[Path] = None

    _conjunction_cache: Optional[Dict[str, Any]] = None
    _uncertainty_cache: Optional[Dict[str, Any]] = None
    _satellites_cache: Optional[List[Dict[str, Any]]] = None
    _trajectories_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def resolve_paths(cls) -> Tuple[Optional[Path], Optional[Path]]:
        if cls._output_dir and cls._data_dir:
            return cls._output_dir, cls._data_dir

        for cand in MEMBER1_OUTPUT_CANDIDATES:
            if cand.exists() and (cand / "conjunction.json").exists():
                cls._output_dir = cand
                break

        for cand in MEMBER1_DATA_CANDIDATES:
            if cand.exists() and (cand / "tle_metadata.csv").exists():
                cls._data_dir = cand
                break

        return cls._output_dir, cls._data_dir

    @classmethod
    def is_available(cls) -> bool:
        out_dir, data_dir = cls.resolve_paths()
        return bool(out_dir and data_dir and (out_dir / "conjunction.json").exists())

    @classmethod
    def load_conjunctions(cls) -> Dict[str, Any]:
        if cls._conjunction_cache is not None:
            return cls._conjunction_cache
        out_dir, _ = cls.resolve_paths()
        if not out_dir:
            raise FileNotFoundError("Member 1 output directory not found.")
        file_path = out_dir / "conjunction.json"
        with open(file_path, "r", encoding="utf-8") as f:
            cls._conjunction_cache = json.load(f)
        return cls._conjunction_cache

    @classmethod
    def load_uncertainty(cls) -> Dict[str, Any]:
        if cls._uncertainty_cache is not None:
            return cls._uncertainty_cache
        out_dir, _ = cls.resolve_paths()
        if not out_dir:
            raise FileNotFoundError("Member 1 output directory not found.")
        file_path = out_dir / "uncertainty.json"
        with open(file_path, "r", encoding="utf-8") as f:
            cls._uncertainty_cache = json.load(f)
        return cls._uncertainty_cache

    @classmethod
    def load_satellites(cls) -> List[Dict[str, Any]]:
        if cls._satellites_cache is not None:
            return cls._satellites_cache
        _, data_dir = cls.resolve_paths()
        if not data_dir:
            raise FileNotFoundError("Member 1 data directory not found.")
        file_path = data_dir / "tle_metadata.csv"
        satellites = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    age_h = float(row.get("tle_age_hours", 0.0))
                except (ValueError, TypeError):
                    age_h = 0.0
                satellites.append({
                    "name": row.get("name", ""),
                    "norad_id": str(row.get("norad_id", "")).strip(),
                    "line1": row.get("line1", ""),
                    "line2": row.get("line2", ""),
                    "epoch": row.get("epoch", ""),
                    "tle_age_hours": age_h,
                })
        cls._satellites_cache = satellites
        return cls._satellites_cache

    @classmethod
    def load_trajectories(cls) -> Dict[str, Any]:
        if cls._trajectories_cache is not None:
            return cls._trajectories_cache
        out_dir, _ = cls.resolve_paths()
        if not out_dir:
            raise FileNotFoundError("Member 1 output directory not found.")
        file_path = out_dir / "trajectories.json"
        with open(file_path, "r", encoding="utf-8") as f:
            cls._trajectories_cache = json.load(f)
        return cls._trajectories_cache

    # ==========================================================================
    # Read-only Query Methods
    # ==========================================================================

    @classmethod
    def get_dataset_freshness(cls) -> DatasetFreshness:
        if not cls.is_available():
            return DatasetFreshness(
                status="unavailable",
                data_freshness_status="stale",
                note="Member 1 datasets not found on filesystem."
            )
        try:
            conjs = cls.load_conjunctions()
            unc = cls.load_uncertainty()
            trajs = cls.load_trajectories()

            meta_c = conjs.get("metadata", {})
            meta_u = unc.get("metadata", {})
            meta_t = trajs.get("metadata", {})

            return DatasetFreshness(
                status="online",
                conjunction_generated_at_utc=meta_c.get("generated_at_utc"),
                uncertainty_generated_at=meta_u.get("generated_at"),
                trajectories_generated_at=meta_t.get("generated_at"),
                trajectory_start_time_utc=meta_t.get("start_time_utc"),
                trajectory_end_time_utc=meta_t.get("end_time_utc"),
                tle_sha256=meta_c.get("tle_sha256") or meta_t.get("tle_sha256"),
                total_satellites=meta_c.get("total_satellites", 200),
                total_conjunctions=len(conjs.get("conjunctions", [])),
                data_freshness_status="fresh",
                note="Member 1 SGP4 propagation and continuous-run minimization screening active.",
            )
        except Exception as exc:
            logger.error("Error reading Member 1 dataset freshness: %s", exc)
            return DatasetFreshness(
                status="error",
                data_freshness_status="degraded",
                note=f"Error reading dataset metadata: {exc}"
            )

    @classmethod
    def get_satellites(
        cls,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> OrbitalSatellitesResponse:
        satellites = cls.load_satellites()
        if search and isinstance(search, str):
            q = search.lower().strip()
            satellites = [
                s for s in satellites
                if q in s["name"].lower() or q in s["norad_id"]
            ]
        total = len(satellites)
        sliced = satellites[offset : offset + limit]
        return OrbitalSatellitesResponse(
            total=total,
            count=len(sliced),
            offset=offset,
            limit=limit,
            items=[OrbitalSatellite(**s) for s in sliced]
        )

    @classmethod
    def get_conjunctions_raw(cls) -> ConjunctionsResponse:
        data = cls.load_conjunctions()
        return ConjunctionsResponse(
            metadata=ConjunctionMetadata(**data["metadata"]),
            conjunctions=[ConjunctionEventM1(**c) for c in data.get("conjunctions", [])]
        )

    @classmethod
    def get_uncertainty_raw(cls) -> UncertaintyResponse:
        data = cls.load_uncertainty()
        return UncertaintyResponse(
            metadata=UncertaintyMetadata(**data["metadata"]),
            satellite_uncertainties=[SatelliteUncertainty(**s) for s in data.get("satellite_uncertainties", [])]
        )

    @classmethod
    def get_sampled_trajectories(
        cls,
        step: int = 15,
        norad_ids: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> TrajectoriesResponse:
        """Returns decimated trajectories for efficient 3D globe rendering.

        step=15 samples every 15 minutes (or 15 sample steps = 15 minutes for 60s intervals),
        transforming 4321 timestamps into 289 points per orbit.
        """
        step = max(1, step)
        data = cls.load_trajectories()

        raw_meta = data["metadata"]
        all_timestamps = data.get("timestamps_utc", [])
        sampled_timestamps = all_timestamps[::step]

        all_trajs = data.get("trajectories", [])

        if norad_ids:
            target_ids = {str(nid).strip() for nid in norad_ids}
            all_trajs = [t for t in all_trajs if str(t["norad_id"]).strip() in target_ids]

        total_matching = len(all_trajs)
        sliced_trajs = all_trajs[offset : offset + limit]

        sampled_results = []
        for t in sliced_trajs:
            pos = t.get("positions_km", [])
            vel = t.get("velocities_km_s", [])
            sampled_results.append(
                SatelliteTrajectorySampled(
                    name=t.get("name", ""),
                    norad_id=str(t.get("norad_id", "")),
                    positions_km=pos[::step],
                    velocities_km_s=vel[::step] if vel else [],
                )
            )

        meta = TrajectoryMetadata(
            generated_at=raw_meta.get("generated_at", ""),
            start_time_utc=raw_meta.get("start_time_utc", ""),
            end_time_utc=raw_meta.get("end_time_utc", ""),
            duration_days=raw_meta.get("duration_days", 3),
            interval_seconds=raw_meta.get("interval_seconds", 60) * step,
            sample_step=step,
            coordinate_frame=raw_meta.get("coordinate_frame", "GCRS"),
            position_unit=raw_meta.get("position_unit", "km"),
            velocity_unit=raw_meta.get("velocity_unit", "km/s"),
            total_satellites=total_matching,
            failed_satellites=raw_meta.get("failed_satellites", 0),
            tle_sha256=raw_meta.get("tle_sha256", ""),
        )

        return TrajectoriesResponse(
            metadata=meta,
            timestamps_utc=sampled_timestamps,
            trajectories=sampled_results,
        )

    @classmethod
    def get_enriched_conjunctions_for_member2(cls, limit: int = 100) -> List[Dict[str, Any]]:
        """Processes Member 1 conjunctions through Member 2 encounter-plane risk model."""
        from app.adapters.member2_adapter import Member2Adapter, ConjunctionAnalysisRequest

        conjs_data = cls.load_conjunctions()
        unc_data = cls.load_uncertainty()

        unc_map = {
            s["norad_id"]: s for s in unc_data.get("satellite_uncertainties", [])
        }

        raw_list = conjs_data.get("conjunctions", [])[:limit]
        enriched = []

        for c in raw_list:
            id1 = str(c["norad_id_1"])
            id2 = str(c["norad_id_2"])
            name1 = c["satellite_1"]
            name2 = c["satellite_2"]
            miss_km = float(c["miss_distance_km"])
            tca_str = c["tca_utc"]

            u1 = unc_map.get(id1, {})
            u2 = unc_map.get(id2, {})
            age1 = float(u1.get("tle_age_hours", 12.0))
            age2 = float(u2.get("tle_age_hours", 12.0))

            scale1 = float(u1.get("uncertainty_scale_km", 0.1))
            scale2 = float(u2.get("uncertainty_scale_km", 0.1))
            combined_scale = round((scale1 + scale2) / 0.2, 3)

            try:
                tca_dt = datetime.fromisoformat(tca_str.replace("Z", "+00:00"))
            except Exception:
                tca_dt = datetime.now(timezone.utc)

            req = ConjunctionAnalysisRequest(
                conjunction_id=f"C-M1-{id1}-{id2}",
                satellite_1_id=f"{name1} ({id1})",
                satellite_2_id=f"{name2} ({id2})",
                tca=tca_dt,
                miss_distance_km=miss_km,
                relative_speed_kms=10.0,
                tle_age_1_h=age1,
                tle_age_2_h=age2,
                uncertainty_scale=combined_scale,
                agent_1_can_manoeuvre=True,
                agent_1_fuel_budget_ms=2.0,
                agent_2_can_manoeuvre=False,
                agent_2_fuel_budget_ms=0.0,
            )

            report = Member2Adapter.run_analysis(req)

            enriched.append({
                "id": f"cnj-{id1}-{id2}",
                "conjunction_id": req.conjunction_id,
                "norad_id_1": id1,
                "norad_id_2": id2,
                "satellite_1": name1,
                "satellite_2": name2,
                "objectA": id1,
                "objectB": id2,
                "tcaIso": tca_str,
                "missDistanceKm": miss_km,
                "relativeVelocityKmS": 10.0,
                "collisionProbability": report.risk_assessment.pc,
                "risk": report.risk_assessment.risk_level.lower(),
                "risk_level": report.risk_assessment.risk_level,
                "anomalyFlag": report.risk_assessment.anomaly_flag,
                "uncertainty_scale_km": scale1 + scale2,
                "tle_age_1_h": age1,
                "tle_age_2_h": age2,
                "notes": report.risk_assessment.notes,
                "manoeuvrePlan": report.manoeuvre_plan.model_dump(),
                "briefingReport": report.briefing_report,
                "isSynthetic": True,
                "source": "Member 1 SGP4 Screening + Member 2 Risk Engine",
                "syntheticWarning": SYNTHETIC_MANOEUVRE_WARNING,
            })

        return enriched
