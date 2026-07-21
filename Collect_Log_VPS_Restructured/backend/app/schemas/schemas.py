import re
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


# Caractères interdits dans un chemin de fichier distant (shell injection)
_FORBIDDEN_PATH_CHARS = re.compile(r'[;&|`$(){}[\]!#~<>]')

class VPSBase(BaseModel):
    name: str
    host: str
    user: str
    port: int = 22
    log_path: Optional[str] = "/var/log/nginx/access.log"

    @field_validator("log_path")
    @classmethod
    def validate_log_path(cls, v: Optional[str]) -> Optional[str]:
        if v and _FORBIDDEN_PATH_CHARS.search(v):
            raise ValueError(
                "log_path contient des caractères interdits "
                "(shell metacharacters)"
            )
        return v


class VPSCreate(VPSBase):
    password: Optional[str] = None
    ssh_key:  Optional[str] = None


class VPSUpdate(BaseModel):
    name:     Optional[str] = None
    host:     Optional[str] = None
    user:     Optional[str] = None
    port:     Optional[int] = None
    log_path: Optional[str] = None
    password: Optional[str] = None
    ssh_key:  Optional[str] = None

    @field_validator("log_path")
    @classmethod
    def validate_log_path(cls, v: Optional[str]) -> Optional[str]:
        if v and _FORBIDDEN_PATH_CHARS.search(v):
            raise ValueError(
                "log_path contient des caractères interdits "
                "(shell metacharacters)"
            )
        return v


class VPSOut(VPSBase):
    id: int
    created_at: datetime
    deleted_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ── Collections ───────────────────────────────────────────────
class CollectionOut(BaseModel):
    id: int
    vps_id: int
    collected_at: datetime
    source_file: Optional[str]
    total_lines: int
    mode: str
    class Config:
        from_attributes = True


# ── Log Entry ─────────────────────────────────────────────────
class LogEntryOut(BaseModel):
    id: int
    ip: Optional[str]
    timestamp: Optional[datetime]
    method: Optional[str]
    path: Optional[str]
    status: Optional[int]
    size: Optional[int]
    response_time: Optional[float]
    class Config:
        from_attributes = True


class PaginatedLogs(BaseModel):
    total: int
    page: int
    size: int
    items: List[LogEntryOut]


# ── Summary ───────────────────────────────────────────────────
class LogSummaryOut(BaseModel):
    id: int
    collection_id: int
    total_requests: int
    unique_ips: int
    error_count: int
    success_count: int
    avg_size: float
    avg_resp_time: float
    top_paths: Optional[str]
    top_ips: Optional[str]
    status_dist: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


# ── Stats globales ────────────────────────────────────────────
class GlobalStats(BaseModel):
    total_requests: int
    total_errors: int
    unique_ips: int
    collections_count: int
    vps_count: int
    error_rate: float
    avg_latency:  Optional[float] = None
    p50_latency:  Optional[float] = None
    p95_latency:  Optional[float] = None
    p99_latency:  Optional[float] = None
    rate_4xx:     Optional[float] = None
    rate_5xx:     Optional[float] = None

# ── Endpoint Stats ────────────────────────────────────────────
class EndpointStatOut(BaseModel):
    id:            int
    collection_id: int
    endpoint:      str

    nb_requetes:   int

    latence_min_ms:  Optional[float]
    latence_p50_ms:  Optional[float]
    latence_moy_ms:  Optional[float]
    latence_p75_ms:  Optional[float]
    latence_p95_ms:  Optional[float]
    latence_p99_ms:  Optional[float]
    latence_max_ms:  Optional[float]
    latence_sum_ms:  Optional[float]

    upstream_moy_ms: Optional[float]
    overhead_moy_ms: Optional[float]

    body_min_mo:  Optional[float]
    body_p50_mo:  Optional[float]
    body_moy_mo:  Optional[float]
    body_p75_mo:  Optional[float]
    body_p95_mo:  Optional[float]
    body_p99_mo:  Optional[float]
    body_max_mo:  Optional[float]
    body_sum_mo:  Optional[float]

    taux_erreur_5xx: Optional[float]
    taux_erreur_4xx: Optional[float]

    premiere_occurrence_utc: Optional[datetime]
    derniere_occurrence_utc:  Optional[datetime]

    class Config:
        from_attributes = True

# ── Auth ──────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_active: int
    created_at: datetime
    class Config:
        from_attributes = True
