"""Small typed messages between the controller, evaluators and account owners."""
from dataclasses import dataclass, field

from .compiler import Program
from .types import Account, AccountKey, Contract, PositionView, Transition, UnitKey


@dataclass(slots=True)
class InstallAccount:
    account: Account
    contracts: dict[int, Contract]
    calendars: dict[str, object]
    programs: dict[UnitKey, Program]


@dataclass(slots=True)
class InstallUnit:
    key: UnitKey
    account: AccountKey
    program: Program
    position: PositionView
    status: str
    checkpoint: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PositionUpdate:
    unit: UnitKey
    position: PositionView


@dataclass(frozen=True, slots=True)
class Persist:
    transition: Transition
    command_id: int | None = None


@dataclass(frozen=True, slots=True)
class Committed:
    account: AccountKey
    revision: int


@dataclass(slots=True)
class Control:
    identity: int
    account: AccountKey
    kind: str
    payload: dict


@dataclass(slots=True)
class SaveControl:
    identity: int
    account: Account
    error: str = ''


@dataclass(frozen=True, slots=True)
class RejectedIntent:
    unit: UnitKey
    identity: str
    reason: str


@dataclass(frozen=True, slots=True)
class PrepareMarket:
    worker: int
    symbol: str
    reason: str


@dataclass(frozen=True, slots=True)
class UnitFailure:
    unit: UnitKey
    error: str


@dataclass(frozen=True, slots=True)
class SessionSettled:
    account: AccountKey
    session_id: int


@dataclass(frozen=True, slots=True)
class EvaluationSaved:
    unit: UnitKey
    account: AccountKey
    version: int
    position_revision: int
    state: dict


@dataclass(frozen=True, slots=True)
class RemoveUnit:
    unit: UnitKey


@dataclass(frozen=True, slots=True)
class RemoveAccount:
    account: AccountKey
