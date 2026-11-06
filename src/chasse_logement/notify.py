from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx

from .config import NotifyConfig, NotifyEmailConfig, NotifyTelegramConfig
from .matching import MatchResult
from .models import Listing, Property


class Notifier(Protocol):
    def send_digest(self, subject: str, results: list[MatchResult]) -> None: ...


def _links(item: Listing | Property) -> str:
    """Liens vers chaque source du bien (un bien peut être présent sur plusieurs sources)."""
    if isinstance(item, Property):
        return " ; ".join(f"{s.source_id} : {s.url}" for s in item.sources if s.url)
    return item.url


def _fmt_result(r: MatchResult) -> str:
    item = r.listing
    ppm = f"{item.price_per_m2:.0f} €/m²" if item.price_per_m2 else "prix/m² n.c."
    source_label = (
        ", ".join(s.source_id for s in item.sources)
        if isinstance(item, Property)
        else item.source_id
    )
    parts = [
        f"{item.title or '(sans titre)'}",
        f"prix : {item.total_price:.0f} €/mois" if item.total_price is not None else "prix : n.c.",
        f"surface : {item.surface_m2:.0f} m²" if item.surface_m2 else "surface : n.c.",
        f"pièces : {item.rooms}" if item.rooms is not None else "pièces : n.c.",
        f"zone : {item.postcode or item.city or 'n.c.'}",
        f"{ppm} — score {r.score:.0f}/100 — sources : {source_label}",
    ]
    if isinstance(item, Property) and item.red_flags:
        parts.append("⚠ à vérifier : " + " ; ".join(item.red_flags))
    parts.append(_links(item))
    return " | ".join(p for p in parts if p)


def build_digest_text(results: list[MatchResult]) -> str:
    lines = [f"- {_fmt_result(r)}" for r in results]
    return "\n".join(lines)


def build_digest_html(results: list[MatchResult]) -> str:
    items = []
    for r in results:
        item = r.listing
        if isinstance(item, Property):
            src_html = " ".join(
                f'<a href="{s.url}">{s.source_id}</a>' for s in item.sources if s.url
            )
            flag = (
                f"<br><b>⚠ à vérifier :</b> {' ; '.join(item.red_flags)}" if item.red_flags else ""
            )
            items.append(
                f"<li><b>{item.title or '(sans titre)'}</b> — "
                f"{item.total_price:.0f} €/mois — {item.surface_m2 or 0:.0f} m² — "
                f"{item.postcode or ''} — score {r.score:.0f}/100<br>"
                f"sources : {src_html}{flag}</li>"
            )
        else:
            link = (
                f'<a href="{item.url}">{item.title or "(sans titre)"}</a>'
                if item.url
                else item.title
            )
            items.append(
                f"<li>{link} — {item.total_price:.0f} €/mois — "
                f"{item.surface_m2 or 0:.0f} m² — {item.postcode or ''} "
                f"— score {r.score:.0f}/100</li>"
            )
    return f"<html><body><ul>{''.join(items)}</ul></body></html>"


class EmailNotifier:
    def __init__(self, cfg: NotifyEmailConfig) -> None:
        self.cfg = cfg

    def send_digest(self, subject: str, results: list[MatchResult]) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.cfg.from_addr
        msg["To"] = ", ".join(self.cfg.to_addrs)
        msg.set_content(build_digest_text(results))
        msg.add_alternative(build_digest_html(results), subtype="html")
        with smtplib.SMTP(self.cfg.smtp_host, self.cfg.smtp_port, timeout=30) as smtp:
            if self.cfg.starttls:
                smtp.starttls()
            if self.cfg.smtp_user:
                smtp.login(self.cfg.smtp_user, self.cfg.password)
            smtp.send_message(msg)


class TelegramNotifier:
    BASE = "https://api.telegram.org"

    def __init__(self, cfg: NotifyTelegramConfig) -> None:
        self.cfg = cfg
        self._client = httpx.Client(base_url=self.BASE, timeout=30.0)

    def send_digest(self, subject: str, results: list[MatchResult]) -> None:
        text = f"*{subject}*\n\n" + "\n".join(f"• {_fmt_result(r)}" for r in results[:20])
        self._client.post(
            f"/bot{self.cfg.bot_token}/sendMessage",
            json={"chat_id": self.cfg.chat_id, "text": text[:4000], "parse_mode": "Markdown"},
        ).raise_for_status()


class CompositeNotifier:
    def __init__(self, notifiers: list[Notifier]) -> None:
        self.notifiers = notifiers

    def send_digest(self, subject: str, results: list[MatchResult]) -> None:
        for n in self.notifiers:
            n.send_digest(subject, results)


def build_notifier(cfg: NotifyConfig) -> Notifier | None:
    notifiers: list[Notifier] = []
    if cfg.email.enabled:
        notifiers.append(EmailNotifier(cfg.email))
    if cfg.telegram.enabled:
        notifiers.append(TelegramNotifier(cfg.telegram))
    if not notifiers:
        return None
    if len(notifiers) == 1:
        return notifiers[0]
    return CompositeNotifier(notifiers)
