from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class HttpConfig(BaseModel):
    user_agent: str = "chasse-logement/0.1 (+https://github.com/standlsg/chasse-logement)"
    min_interval_s: float = 2.0
    respect_robots: bool = True
    timeout_s: float = 20.0


class ImapConfig(BaseModel):
    enabled: bool = False
    host: str = ""
    port: int = 993
    user: str = ""
    password: str = ""
    mailbox: str = "INBOX"
    since_days: int = 2
    portals: list[str] = Field(default_factory=list)  # vide = tous les portails


class RssFeedConfig(BaseModel):
    name: str
    url: str
    enabled: bool = True


class ApiAggregatorConfig(BaseModel):
    enabled: bool = False
    base_url: str = ""
    api_key: str = ""


class SourcesConfig(BaseModel):
    imap: ImapConfig = Field(default_factory=ImapConfig)
    rss_feeds: list[RssFeedConfig] = Field(default_factory=list)
    api: ApiAggregatorConfig = Field(default_factory=ApiAggregatorConfig)


class Criteria(BaseModel):
    budget_max: float = 2000.0
    min_surface_m2: float = 0.0
    min_rooms: int = 0
    postcodes: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    center_latitude: float | None = None
    center_longitude: float | None = None
    radius_km: float | None = None
    furnished: bool | None = None
    exclude_keywords: list[str] = Field(default_factory=list)
    min_score: float = 50.0


class NotifyEmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    password: str = ""
    from_addr: str = ""
    to_addrs: list[str] = Field(default_factory=list)
    starttls: bool = True


class NotifyTelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class NotifyConfig(BaseModel):
    mode: Literal["digest", "instant"] = "digest"
    email: NotifyEmailConfig = Field(default_factory=NotifyEmailConfig)
    telegram: NotifyTelegramConfig = Field(default_factory=NotifyTelegramConfig)


class ScheduleConfig(BaseModel):
    hour: int = 8
    minute: int = 0
    interval_hours: int = 24


class AppConfig(BaseModel):
    database_path: str = "data/chasse-logement.db"
    http: HttpConfig = Field(default_factory=HttpConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    criteria: Criteria = Field(default_factory=Criteria)
    notify: NotifyConfig = Field(default_factory=NotifyConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)


class Secrets(BaseSettings):
    """Secrets lus depuis l'environnement / .env (préfixe CL_)."""

    model_config = SettingsConfigDict(env_prefix="CL_", env_file=".env", extra="ignore")

    imap_password: str | None = None
    smtp_password: str | None = None
    telegram_token: str | None = None
    api_key: str | None = None


def load_config(path: str | Path) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    cfg = AppConfig.model_validate(raw)
    secrets = Secrets()
    if secrets.imap_password:
        cfg.sources.imap.password = secrets.imap_password
    if secrets.smtp_password:
        cfg.notify.email.password = secrets.smtp_password
    if secrets.telegram_token:
        cfg.notify.telegram.bot_token = secrets.telegram_token
    if secrets.api_key:
        cfg.sources.api.api_key = secrets.api_key
    return cfg
