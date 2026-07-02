from enum import Enum


class PricingUnit(str, Enum):
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    TOKEN = "token"
    PACKAGE = "package"


class InstanceStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    EXPIRED = "expired"
    RELEASED = "released"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionKind(str, Enum):
    RECHARGE = "recharge"
    ORDER_PAYMENT = "order_payment"
    CONSUMPTION = "consumption"
    REFUND = "refund"


class RechargeStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
