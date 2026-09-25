"""
Dispatch Package for Resonance (Phase 5).
Controlled Dispatch Engine, Delivery Telemetry & Campaign Analytics.
"""

from dispatch.models import (
    DispatchQueueItem,
    PreflightReport,
    SuppressionRecord,
    DeliveryLogEvent,
    AuditLogEntry,
    DispatchConfirmPayload,
    TestSendPayload,
    SuppressionCreatePayload
)
from dispatch.suppression import SuppressionManager
from dispatch.delivery_log import DeliveryLogger, AuditLogger
from dispatch.rate_limiter import RateLimiter
from dispatch.eligibility import FinalEligibilityChecker, EligibilityResult
from dispatch.queue import DispatchQueue
from dispatch.sender import DispatchSender
from dispatch.dispatcher import DispatchCoordinator
from dispatch.analytics import AnalyticsService

__all__ = [
    "DispatchQueueItem",
    "PreflightReport",
    "SuppressionRecord",
    "DeliveryLogEvent",
    "AuditLogEntry",
    "DispatchConfirmPayload",
    "TestSendPayload",
    "SuppressionCreatePayload",
    "SuppressionManager",
    "DeliveryLogger",
    "AuditLogger",
    "RateLimiter",
    "FinalEligibilityChecker",
    "EligibilityResult",
    "DispatchQueue",
    "DispatchSender",
    "DispatchCoordinator",
    "AnalyticsService"
]
