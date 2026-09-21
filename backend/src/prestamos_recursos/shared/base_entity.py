from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class BaseEntity:
    """Base de todos los Aggregate Roots: identidad por UUID."""

    id: UUID = field(default_factory=uuid4)
