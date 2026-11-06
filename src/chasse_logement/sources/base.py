from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from ..models import Listing, SourceKind


class Source(Protocol):
    """Tout connecteur de source produit des Listing normalisés."""

    name: str
    kind: SourceKind

    def collect(self) -> Iterator[Listing]: ...
