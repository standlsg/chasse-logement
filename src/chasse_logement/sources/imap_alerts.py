"""Connecteur IMAP : lit les emails d'alerte des portails dans une boîte dédiée.

Conformité : on parse UNIQUEMENT le contenu des emails reçus dans la propre boîte de
l'utilisateur (compte portail + alertes email activées). On ne fetch JAMAIS les pages
des portails (Leboncoin, SeLoger, PAP, Bien'ici, Logic-Immo : CGU + droit sui generis).
"""

from __future__ import annotations

import imaplib
import re
from collections.abc import Iterator
from datetime import date, timedelta
from email import policy
from email.message import Message
from email.parser import BytesParser

from ..models import Listing, SourceKind
from .parsing import (
    extract_listing_urls,
    extract_postcode,
    extract_price,
    extract_rooms,
    extract_surface,
    strip_tags,
)

PORTAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("leboncoin", re.compile(r"leboncoin", re.IGNORECASE)),
    ("seloger", re.compile(r"seloger", re.IGNORECASE)),
    ("pap", re.compile(r"\bpap\b|particulier.?a.?particulier", re.IGNORECASE)),
    ("bienici", re.compile(r"bien'?ici", re.IGNORECASE)),
    ("logic-immo", re.compile(r"logic.?immo", re.IGNORECASE)),
]


def detect_portal(from_header: str, subject: str) -> str:
    haystack = f"{from_header}\n{subject}"
    for name, pattern in PORTAL_PATTERNS:
        if pattern.search(haystack):
            return name
    return "portail"


def _body_parts(msg: Message) -> tuple[str, str]:
    text_parts: list[str] = []
    html_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                text_parts.append(part.get_content())
            elif ctype == "text/html":
                html_parts.append(part.get_content())
    else:
        if msg.get_content_type() == "text/html":
            html_parts.append(msg.get_content())
        else:
            text_parts.append(msg.get_content())
    return "\n".join(text_parts), "\n".join(html_parts)


def parse_alert_email(raw: bytes) -> Listing | None:
    """Transforme un email d'alerte brut en Listing (sans fetcher aucune page)."""
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    subject = str(msg.get("Subject", "")).strip()
    from_header = str(msg.get("From", ""))
    text_body, html_body = _body_parts(msg)
    full_text = "\n".join([subject, text_body, strip_tags(html_body)])
    urls = extract_listing_urls(html_body or text_body)
    url = urls[0] if urls else ""
    message_id = str(msg.get("Message-ID", "")).strip()
    if not subject and not url:
        return None
    return Listing(
        source_id=detect_portal(from_header, subject),
        source_kind=SourceKind.IMAP_ALERT,
        external_id=message_id or url or subject,
        url=url,
        title=subject,
        price=extract_price(full_text),
        surface_m2=extract_surface(full_text),
        rooms=extract_rooms(full_text),
        postcode=extract_postcode(full_text),
        description=text_body[:2000] or strip_tags(html_body)[:2000],
        publisher=from_header,
    )


class ImapAlertsSource:
    """Collecte les emails d'alerte reçus depuis `since_days` dans la boîte dédiée."""

    kind = SourceKind.IMAP_ALERT

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        mailbox: str = "INBOX",
        since_days: int = 2,
        name: str = "alertes-mail",
    ) -> None:
        self.name = name
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.mailbox = mailbox
        self.since_days = since_days

    def collect(self) -> Iterator[Listing]:
        since = (date.today() - timedelta(days=self.since_days)).strftime("%d-%b-%Y")
        imap = imaplib.IMAP4_SSL(self.host, self.port)
        try:
            imap.login(self.user, self.password)
            imap.select(self.mailbox)
            _typ, data = imap.search(None, f"(SINCE {since})")
            for num in data[0].split():
                _typ, msg_data = imap.fetch(num, "(RFC822)")
                raw = msg_data[0][1]
                listing = parse_alert_email(raw)
                if listing is not None:
                    yield listing
        finally:
            try:
                imap.logout()
            except imaplib.IMAP4.error:
                pass
