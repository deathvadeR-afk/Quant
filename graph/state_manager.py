"""
Redis-backed State Manager for LangGraph.

Provides persistent state storage with:
- State versioning and audit trail
- State backup/restore
- Connection pooling
- Retry logic
"""

from typing import Optional
import json
import logging
from datetime import datetime

from graph.state import TradingState

logger = logging.getLogger(__name__)


class RedisStateManager:
    """
    Redis-backed state manager for trading graph.
    
    Features:
    - Persistent state storage
    - State versioning
    - Audit trail
    - Backup/restore
    - Connection pooling
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "trading_graph:",
        connection_timeout: float = 5.0,
        operation_timeout: float = 0.1,
    ):
        """
        Initialize Redis state manager.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            key_prefix: Prefix for all keys
            connection_timeout: Connection timeout in seconds
            operation_timeout: Operation timeout in seconds
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key_prefix = key_prefix
        self.connection_timeout = connection_timeout
        self.operation_timeout = operation_timeout
        
        self._client: Optional["redis.Redis"] = None
    
    def _get_client(self) -> "redis.Redis":
        """Get or create Redis client with connection pooling."""
        if self._client is None:
            import redis
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                socket_timeout=self.operation_timeout,
                socket_connect_timeout=self.connection_timeout,
                max_connections=10,
            )
            self._client = redis.Redis(connection_pool=pool)
        return self._client
    
    def _state_key(self, cycle_id: str) -> str:
        """Generate Redis key for state."""
        return f"{self.key_prefix}state:{cycle_id}"
    
    def _version_key(self, cycle_id: str) -> str:
        """Generate Redis key for state version."""
        return f"{self.key_prefix}version:{cycle_id}"
    
    def _audit_key(self, cycle_id: str) -> str:
        """Generate Redis key for audit trail."""
        return f"{self.key_prefix}audit:{cycle_id}"
    
    def save_state(self, cycle_id: str, state: TradingState) -> bool:
        """
        Save state to Redis.
        
        Args:
            cycle_id: Unique cycle identifier
            state: TradingState to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            
            # Serialize state
            state_json = state.model_dump_json()
            
            # Get current version
            current_version = client.get(self._version_key(cycle_id))
            new_version = (int(current_version.decode()) + 1) if current_version else 1
            
            # Save state with version
            pipe = client.pipeline()
            pipe.set(self._state_key(cycle_id), state_json)
            pipe.set(self._version_key(cycle_id), str(new_version))
            
            # Add to audit trail
            audit_entry = json.dumps({
                "timestamp": datetime.now().isoformat(),
                "version": new_version,
                "agent": state.current_agent,
                "status": state.agent_status.value if hasattr(state.agent_status, 'value') else state.agent_status,
            })
            pipe.rpush(self._audit_key(cycle_id), audit_entry)
            
            # Set TTL of 7 days for state, 30 days for audit
            pipe.expire(self._state_key(cycle_id), 7 * 24 * 60 * 60)
            pipe.expire(self._audit_key(cycle_id), 30 * 24 * 60 * 60)
            
            pipe.execute()
            
            logger.info(f"Saved state for cycle {cycle_id}, version {new_version}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save state for cycle {cycle_id}: {e}")
            return False
    
    def load_state(self, cycle_id: str) -> Optional[TradingState]:
        """
        Load state from Redis.
        
        Args:
            cycle_id: Unique cycle identifier
            
        Returns:
            TradingState if found, None otherwise
        """
        try:
            client = self._get_client()
            
            state_json = client.get(self._state_key(cycle_id))
            
            if state_json is None:
                logger.debug(f"No state found for cycle {cycle_id}")
                return None
            
            state = TradingState.model_validate_json(state_json)
            logger.info(f"Loaded state for cycle {cycle_id}")
            return state
        
        except Exception as e:
            logger.error(f"Failed to load state for cycle {cycle_id}: {e}")
            return None
    
    def get_version(self, cycle_id: str) -> int:
        """
        Get current version number for cycle.
        
        Args:
            cycle_id: Unique cycle identifier
            
        Returns:
            Version number, 0 if not found
        """
        try:
            client = self._get_client()
            version = client.get(self._version_key(cycle_id))
            return int(version.decode()) if version else 0
        except Exception as e:
            logger.error(f"Failed to get version for cycle {cycle_id}: {e}")
            return 0
    
    def get_audit_trail(self, cycle_id: str) -> list:
        """
        Get audit trail for cycle.
        
        Args:
            cycle_id: Unique cycle identifier
            
        Returns:
            List of audit entries
        """
        try:
            client = self._get_client()
            entries = client.lrange(self._audit_key(cycle_id), 0, -1)
            return [json.loads(e.decode()) for e in entries]
        except Exception as e:
            logger.error(f"Failed to get audit trail for cycle {cycle_id}: {e}")
            return []
    
    def delete_state(self, cycle_id: str) -> bool:
        """
        Delete state and related data for cycle.
        
        Args:
            cycle_id: Unique cycle identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            
            pipe = client.pipeline()
            pipe.delete(self._state_key(cycle_id))
            pipe.delete(self._version_key(cycle_id))
            pipe.delete(self._audit_key(cycle_id))
            pipe.execute()
            
            logger.info(f"Deleted state for cycle {cycle_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete state for cycle {cycle_id}: {e}")
            return False
    
    def list_cycles(self, limit: int = 100) -> list:
        """
        List all cycle IDs.
        
        Args:
            limit: Maximum number of cycles to return
            
        Returns:
            List of cycle IDs
        """
        try:
            client = self._get_client()
            pattern = f"{self.key_prefix}state:*"
            keys = client.keys(pattern)
            
            cycles = [k.decode().replace(f"{self.key_prefix}state:", "") for k in keys]
            return sorted(cycles, reverse=True)[:limit]
        
        except Exception as e:
            logger.error(f"Failed to list cycles: {e}")
            return []
    
    def backup_state(self, cycle_id: str, backup_id: str) -> bool:
        """
        Create a backup of current state.
        
        Args:
            cycle_id: Cycle to backup
            backup_id: Unique backup identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            state = self.load_state(cycle_id)
            if state is None:
                return False
            
            client = self._get_client()
            backup_key = f"{self.key_prefix}backup:{backup_id}"
            client.set(backup_key, state.model_dump_json())
            client.expire(backup_key, 30 * 24 * 60 * 60)  # 30 days
            
            logger.info(f"Created backup {backup_id} for cycle {cycle_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to backup cycle {cycle_id}: {e}")
            return False
    
    def restore_state(self, backup_id: str, cycle_id: str) -> bool:
        """
        Restore state from backup.
        
        Args:
            backup_id: Backup identifier
            cycle_id: Target cycle ID for restored state
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self._get_client()
            backup_key = f"{self.key_prefix}backup:{backup_id}"
            
            backup_json = client.get(backup_key)
            if backup_json is None:
                logger.error(f"Backup {backup_id} not found")
                return False
            
            state = TradingState.model_validate_json(backup_json.decode())
            return self.save_state(cycle_id, state)
        
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False
    
    def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("Closed Redis connection")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()