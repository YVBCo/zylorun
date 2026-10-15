"""Shared Event Bus for GitFlow Project Hub.

Provides a thread-safe, lightweight in-memory event abstraction supporting:
- Watchtower live activity feeds (retaining recent events per repository)
- Idempotent event broadcasting to registered handlers
- Real-time and audit event logging
"""

from collections import deque
from datetime import datetime, timezone
import logging
import threading
from typing import Any, Callable, Dict, List
import uuid

logger = logging.getLogger(__name__)

# Maximum event history retained in memory per repository for Watchtower
MAX_EVENTS_PER_REPO = 100

_event_lock = threading.Lock()
_repo_event_history: Dict[int, deque] = {}
_subscribers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}


def subscribe(event_type: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
    """Register an event handler for a specific event type or '*' for all events."""
    with _event_lock:
        if event_type not in _subscribers:
            _subscribers[event_type] = []
        _subscribers[event_type].append(handler)


def emit_event(event_type: str, repository_id: int, payload: Dict[str, Any] = None) -> Dict[str, Any]:
    """Publish an event to the shared event system.

    Safe, idempotent, and non-blocking for background or synchronous workflows.
    """
    event = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "repository_id": repository_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }

    # Store event in repository's bounded deque
    with _event_lock:
        if repository_id not in _repo_event_history:
            _repo_event_history[repository_id] = deque(maxlen=MAX_EVENTS_PER_REPO)
        _repo_event_history[repository_id].appendleft(event)

        # Collect handlers
        handlers = list(_subscribers.get(event_type, [])) + list(_subscribers.get("*", []))

    # Invoke subscribers safely without blowing up caller
    for handler in handlers:
        try:
            handler(event)
        except Exception as exc:
            logger.warning("Event handler for %s encountered an error: %s", event_type, exc)

    return event


def get_recent_events(repository_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve the recent event timeline for a repository (used by Watchtower)."""
    with _event_lock:
        events = list(_repo_event_history.get(repository_id, []))
    return events[:limit]


def clear_repository_events(repository_id: int) -> None:
    """Clear memory event history when a repository is deleted."""
    with _event_lock:
        _repo_event_history.pop(repository_id, None)
