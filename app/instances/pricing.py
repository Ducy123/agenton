from datetime import timedelta

from app.common.enums import PricingUnit

# Token/package pricing meters usage per call instead of expiring on a
# clock, so those two units are deliberately absent here — they get no
# fixed rental window (see instances.service.execute_instance_task).
TIME_BASED_DURATIONS: dict[PricingUnit, timedelta] = {
    PricingUnit.HOUR: timedelta(hours=1),
    PricingUnit.DAY: timedelta(days=1),
    PricingUnit.MONTH: timedelta(days=30),
}
