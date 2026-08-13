import threading
from typing import Dict, Any, Optional

class SessionStore:
    """
    Thread-safe, memory-bounded session store for caching PDF extraction previews and exports.
    Automatically evicts the oldest session when capacity is reached.
    """
    def __init__(self, max_sessions: int = 50):
        self.max_sessions = max_sessions
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def set(self, session_id: str, data: Dict[str, Any]) -> None:
        with self._lock:
            # Enforce max capacity eviction before adding new session
            while len(self._sessions) >= self.max_sessions:
                oldest_key = next(iter(self._sessions))
                del self._sessions[oldest_key]
            self._sessions[session_id] = data

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

# Global session store instance
session_store = SessionStore(max_sessions=50)
