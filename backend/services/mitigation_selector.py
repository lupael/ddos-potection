"""
Intelligent mitigation action selection and auto-escalation.

Provides an attack-type-to-action mapping and manages automatic escalation
through increasingly aggressive mitigation steps when an incident is not
resolved within the configured timeout.
"""
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class MitigationSelector:
    """Selects the appropriate mitigation action for a given attack type and escalation level."""

    ATTACK_TYPE_MATRIX: dict = {
        "syn_flood": [
            "rate_limit_syn",
            "iptables_block",
            "flowspec_block",
            "bgp_blackhole",
        ],
        "udp_flood": [
            "rate_limit_udp",
            "iptables_block",
            "flowspec_block",
            "bgp_blackhole",
        ],
        "dns_amplification": [
            "block_udp_53",
            "flowspec_block",
            "bgp_blackhole",
        ],
        "ntp_amplification": [
            "block_udp_123",
            "flowspec_block",
            "bgp_blackhole",
        ],
        "memcached": [
            "block_udp_11211",
            "flowspec_block",
            "bgp_blackhole",
        ],
        "http_flood": [
            "rate_limit_http",
            "ip_reputation_block",
            "bgp_blackhole",
        ],
        "default": [
            "rate_limit",
            "iptables_block",
            "flowspec_block",
            "bgp_blackhole",
        ],
    }

    def select_action(self, attack_type: str, escalation_level: int = 0) -> str:
        """Return the mitigation action for the given attack type and escalation level.

        Args:
            attack_type: The detected attack type (e.g., "syn_flood").
            escalation_level: Zero-based index into the escalation chain.
                If the level exceeds the chain length the last action is returned.

        Returns:
            The action string at the requested escalation level.
        """
        chain = self.get_escalation_chain(attack_type)
        idx = max(0, min(escalation_level, len(chain) - 1))
        return chain[idx]

    def get_escalation_chain(self, attack_type: str) -> list[str]:
        """Return the full ordered escalation chain for the given attack type.

        Args:
            attack_type: The detected attack type.

        Returns:
            List of action strings from least to most aggressive.
            Falls back to the "default" chain for unknown attack types.
        """
        return list(
            self.ATTACK_TYPE_MATRIX.get(
                attack_type.lower(),
                self.ATTACK_TYPE_MATRIX["default"],
            )
        )


class AutoEscalationManager:
    """Tracks mitigation attempts per incident and decides when to escalate.

    State is persisted in Redis (keyed by incident ID) so it survives restarts
    and is consistent across multiple worker processes.  An in-process dict is
    used as a fallback when no Redis client is provided.
    """

    _ATTEMPT_KEY_PREFIX = "escalation:attempts:"
    _TIMESTAMP_KEY_PREFIX = "escalation:ts:"

    def __init__(self, redis_client=None, escalation_timeout_mins: int = 5) -> None:
        """Initialise the escalation manager.

        Args:
            redis_client: An initialised Redis client instance.
            escalation_timeout_mins: Minutes to wait before escalating (default 5).
        """
        self._redis = redis_client
        self.escalation_timeout_secs = escalation_timeout_mins * 60
        self._local_attempts: dict = {}
        self._local_ts: dict = {}
        self._selector = MitigationSelector()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _attempt_key(self, incident_id: str) -> str:
        return f"{self._ATTEMPT_KEY_PREFIX}{incident_id}"

    def _ts_key(self, incident_id: str) -> str:
        return f"{self._TIMESTAMP_KEY_PREFIX}{incident_id}"

    def _get_attempts(self, incident_id: str) -> list[str]:
        key = self._attempt_key(incident_id)
        if self._redis is not None:
            try:
                raw = self._redis.lrange(key, 0, -1)
                if raw:
                    return [v.decode() if isinstance(v, bytes) else v for v in raw]
                return []
            except Exception as exc:
                logger.error("AutoEscalationManager Redis error (get_attempts): %s", exc)
        return list(self._local_attempts.get(key, []))

    def _get_first_ts(self, incident_id: str) -> Optional[float]:
        key = self._ts_key(incident_id)
        if self._redis is not None:
            try:
                val = self._redis.get(key)
                return float(val) if val else None
            except Exception as exc:
                logger.error("AutoEscalationManager Redis error (get_ts): %s", exc)
        return self._local_ts.get(key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_mitigation_attempt(self, incident_id: str, action: str) -> None:
        """Record a mitigation action attempt for an incident.

        Args:
            incident_id: Unique identifier for the incident.
            action: The mitigation action that was applied.
        """
        now = time.time()
        attempt_key = self._attempt_key(incident_id)
        ts_key = self._ts_key(incident_id)

        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.rpush(attempt_key, action)
                # Expire keys after 24 h to avoid unbounded growth
                pipe.expire(attempt_key, 86400)
                if self._redis.get(ts_key) is None:
                    pipe.set(ts_key, now, ex=86400)
                pipe.execute()
                return
            except Exception as exc:
                logger.error("AutoEscalationManager Redis error (record): %s", exc)

        # Fallback to in-process storage
        if attempt_key not in self._local_attempts:
            self._local_attempts[attempt_key] = []
        self._local_attempts[attempt_key].append(action)
        if ts_key not in self._local_ts:
            self._local_ts[ts_key] = now

    def should_escalate(self, incident_id: str) -> bool:
        """Return True if the escalation timeout has elapsed without resolution.

        Args:
            incident_id: Unique identifier for the incident.

        Returns:
            True if at least one attempt has been recorded AND the timeout has
            elapsed since the first attempt.
        """
        first_ts = self._get_first_ts(incident_id)
        if first_ts is None:
            return False
        elapsed = time.time() - first_ts
        return elapsed >= self.escalation_timeout_secs

    def get_next_action(self, incident_id: str, attack_type: str) -> Optional[str]:
        """Determine the next escalation action for an incident.

        Returns the action at the next escalation level (number of recorded
        attempts), or None if the chain is exhausted.

        Args:
            incident_id: Unique identifier for the incident.
            attack_type: The detected attack type used to look up the chain.

        Returns:
            Next action string, or None if no further escalation is available.
        """
        attempts = self._get_attempts(incident_id)
        next_level = len(attempts)
        chain = self._selector.get_escalation_chain(attack_type)
        if next_level >= len(chain):
            logger.warning(
                "AutoEscalationManager: escalation chain exhausted for incident %s (%s)",
                incident_id, attack_type,
            )
            return None
        return chain[next_level]
