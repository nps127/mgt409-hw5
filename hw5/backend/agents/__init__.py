"""The Campus Customs agent team. Every agent can delegate to every other."""

from models import AgentName

from . import accounting, boss, customer_service, facilities, inventory
from .base import AgentSpec

SPECS: dict[AgentName, AgentSpec] = {
    m.SPEC.name: m.SPEC for m in (boss, inventory, accounting, facilities, customer_service)
}
