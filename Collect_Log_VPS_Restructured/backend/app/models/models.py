from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, BigInteger, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from app.core.database import Base
from app.core.crypto import EncryptedText


class VPSServer(Base):
    """Inventaire des serveurs VPS"""
    __tablename__ = "vps_servers"
    # Unicité du nom seulement parmi les VPS actifs (deleted_at IS NULL),
    # pour autoriser la réutilisation d'un nom après suppression logique.
    __table_args__ = (
        Index(
            "uq_vps_servers_name_active",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)   # unicité gérée par l'index partiel ci-dessus
    host       = Column(String(255), nullable=False)
    user       = Column(String(100), nullable=False, default="root")
    port       = Column(Integer, default=22)
    log_path   = Column(String(500), nullable=True, default="/var/log/nginx/access.log")
    # Authentification — chiffrée au repos (Fernet) via EncryptedText
    password   = Column(EncryptedText, nullable=True)
    ssh_key    = Column(EncryptedText, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # suppression logique (soft delete)
    # Curseur de collecte incrémentale : position (octets) déjà lue dans le
    # fichier de logs distant, pour ne récupérer que le nouveau contenu.
    collect_offset = Column(BigInteger, nullable=False, server_default="0", default=0)

    collections = relationship(
        "LogCollection", back_populates="vps",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class LogCollection(Base):
    """Une session de collecte de logs"""
    __tablename__ = "log_collections"

    id           = Column(Integer, primary_key=True, index=True)
    vps_id       = Column(Integer, ForeignKey("vps_servers.id", ondelete="CASCADE"), nullable=False)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    source_file  = Column(String(500))
    total_lines  = Column(Integer, default=0)
    mode         = Column(String(20), default="ssh")  # ssh | mock

    vps     = relationship("VPSServer", back_populates="collections")
    entries = relationship(
        "LogEntry", back_populates="collection",
        cascade="all, delete-orphan", passive_deletes=True,
    )
    summary = relationship(
        "LogSummary", back_populates="collection", uselist=False,
        cascade="all, delete-orphan", passive_deletes=True,
    )


class LogEntry(Base):
    """Entrée individuelle de log Nginx parsée"""
    __tablename__ = "log_entries"
    # Unicité du contenu par VPS : empêche la réinsertion d'une même ligne
    # collectée dans deux fenêtres qui se chevauchent (déduplication).
    __table_args__ = (
        Index("uq_log_entries_vps_hash", "vps_id", "line_hash", unique=True),
    )

    id            = Column(BigInteger, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("log_collections.id", ondelete="CASCADE"), nullable=False)
    # Dénormalisé depuis la collection pour porter l'unicité du contenu par VPS.
    vps_id        = Column(Integer, ForeignKey("vps_servers.id", ondelete="CASCADE"), nullable=False, index=True)
    # Empreinte md5 des champs bruts de la ligne (clé naturelle de déduplication).
    line_hash     = Column(String(32), nullable=False)
    ip            = Column(String(45))
    timestamp     = Column(DateTime(timezone=True))
    method        = Column(String(10))
    path          = Column(Text)
    status        = Column(Integer)
    size          = Column(BigInteger, default=0)
    referrer      = Column(Text)
    user_agent    = Column(Text)
    response_time = Column(Float)

    collection = relationship("LogCollection", back_populates="entries")


class LogSummary(Base):
    """Résumé analytique d'une collection"""
    __tablename__ = "log_summaries"

    id            = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("log_collections.id", ondelete="CASCADE"), unique=True)
    total_requests = Column(Integer, default=0)
    unique_ips     = Column(Integer, default=0)
    error_count    = Column(Integer, default=0)
    success_count  = Column(Integer, default=0)
    avg_size       = Column(Float, default=0.0)
    avg_resp_time  = Column(Float, default=0.0)
    top_paths      = Column(Text)   # JSON string
    top_ips        = Column(Text)   # JSON string
    status_dist    = Column(Text)   # JSON string
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    collection = relationship("LogCollection", back_populates="summary")

class EndpointStat(Base):
    """Statistiques agrégées par endpoint pour une collection donnée"""
    __tablename__ = "endpoint_stats"

    id            = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("log_collections.id", ondelete="CASCADE"), nullable=False)
    endpoint      = Column(Text, nullable=False)

    # Comptage
    nb_requetes   = Column(Integer, default=0)

    # Latence (ms) — request_time
    latence_min_ms   = Column(Float, nullable=True)
    latence_p50_ms   = Column(Float, nullable=True)
    latence_moy_ms   = Column(Float, nullable=True)
    latence_p75_ms   = Column(Float, nullable=True)
    latence_p95_ms   = Column(Float, nullable=True)
    latence_p99_ms   = Column(Float, nullable=True)
    latence_max_ms   = Column(Float, nullable=True)
    latence_sum_ms   = Column(Float, nullable=True)

    # Upstream & overhead (ms) — optionnels si disponibles dans le CSV
    upstream_moy_ms  = Column(Float, nullable=True)
    overhead_moy_ms  = Column(Float, nullable=True)

    # Body size (Mo)
    body_min_mo   = Column(Float, nullable=True)
    body_p50_mo   = Column(Float, nullable=True)
    body_moy_mo   = Column(Float, nullable=True)
    body_p75_mo   = Column(Float, nullable=True)
    body_p95_mo   = Column(Float, nullable=True)
    body_p99_mo   = Column(Float, nullable=True)
    body_max_mo   = Column(Float, nullable=True)
    body_sum_mo   = Column(Float, nullable=True)

    # Taux d'erreur
    taux_erreur_5xx = Column(Float, nullable=True)
    taux_erreur_4xx = Column(Float, nullable=True)

    # Plage temporelle
    premiere_occurrence_utc = Column(DateTime(timezone=True), nullable=True)
    derniere_occurrence_utc  = Column(DateTime(timezone=True), nullable=True)

    collection = relationship("LogCollection")

class User(Base):
    """Utilisateurs de la plateforme (authentification)"""
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(500), nullable=False)
    full_name       = Column(String(200), nullable=True)
    role            = Column(String(50), default="viewer")   # admin | viewer
    is_active       = Column(Integer, default=1)             # 1=actif, 0=désactivé
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    last_login      = Column(DateTime(timezone=True), nullable=True)


class IpEnrichment(Base):
    """
    Cache d'enrichissement par adresse IP (RM-34) : géolocalisation + réputation
    issues d'API externes. Clé globale (indépendante du VPS) avec TTL sur
    `fetched_at`. `is_private` marque les IP locales/réservées (pas d'appel externe).
    """
    __tablename__ = "ip_enrichment"

    ip           = Column(String(45), primary_key=True)
    is_private   = Column(Boolean, default=False)
    country_code = Column(String(2),  nullable=True)
    country      = Column(String(100), nullable=True)
    city         = Column(String(100), nullable=True)
    isp          = Column(String(200), nullable=True)
    abuse_score  = Column(Integer, nullable=True)   # 0–100 (AbuseIPDB)
    is_malicious = Column(Boolean, nullable=True)
    providers    = Column(String(100), nullable=True)  # fournisseurs ayant répondu
    fetched_at   = Column(DateTime(timezone=True), server_default=func.now())
