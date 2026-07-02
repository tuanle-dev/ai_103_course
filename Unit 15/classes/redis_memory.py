import json
from datetime import datetime


class RedisMemory:
    """
    Manages short-term session memory using Redis.
    Stores conversation history and session state with TTL expiration.
    """

    def __init__(self, redis_client, config):
        self.redis_client = redis_client
        self.ttl_seconds = config["redis"]["session_ttl_seconds"]
        self.max_messages_in_history = config["redis"]["max_messages_in_history"]
        self.in_memory_cache = {}  # Fallback when Redis is unavailable

    def _get_key(self, session_id, key_type):
        """Generate a Redis key for a session."""
        return f"session:{session_id}:{key_type}"

    def save_conversation(self, session_id, messages):
        """Save conversation messages to memory (keeps last N messages)."""
        trimmed_messages = messages[-self.max_messages_in_history :]
        data = json.dumps(trimmed_messages)

        if self.redis_client:
            key = self._get_key(session_id, "messages")
            self.redis_client.setex(key, self.ttl_seconds, data)
        else:
            self.in_memory_cache[self._get_key(session_id, "messages")] = {
                "data": data,
                "expires_at": datetime.now().timestamp() + self.ttl_seconds,
            }

    def load_conversation(self, session_id):
        """Load conversation messages from memory."""
        if self.redis_client:
            key = self._get_key(session_id, "messages")
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return []
        else:
            key = self._get_key(session_id, "messages")
            cached = self.in_memory_cache.get(key)
            if cached and cached["expires_at"] > datetime.now().timestamp():
                return json.loads(cached["data"])
            return []

    def save_state(self, session_id, state):
        """Save session state (e.g., awaiting_approval, pending_tool_call)."""
        data = json.dumps(state)

        if self.redis_client:
            key = self._get_key(session_id, "state")
            self.redis_client.setex(key, self.ttl_seconds, data)
        else:
            self.in_memory_cache[self._get_key(session_id, "state")] = {
                "data": data,
                "expires_at": datetime.now().timestamp() + self.ttl_seconds,
            }

    def load_state(self, session_id):
        """Load session state from memory."""
        if self.redis_client:
            key = self._get_key(session_id, "state")
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return {}
        else:
            key = self._get_key(session_id, "state")
            cached = self.in_memory_cache.get(key)
            if cached and cached["expires_at"] > datetime.now().timestamp():
                return json.loads(cached["data"])
            return {}

    def refresh_ttl(self, session_id):
        """Refresh expiration time for all session data."""
        if self.redis_client:
            for key_type in ["messages", "state"]:
                key = self._get_key(session_id, key_type)
                self.redis_client.expire(key, self.ttl_seconds)

    def clear_session(self, session_id):
        """Clear all data for a session."""
        if self.redis_client:
            for key_type in ["messages", "state"]:
                key = self._get_key(session_id, key_type)
                self.redis_client.delete(key)
        else:
            for key_type in ["messages", "state"]:
                key = self._get_key(session_id, key_type)
                self.in_memory_cache.pop(key, None)
