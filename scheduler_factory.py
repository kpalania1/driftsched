# scheduler_factory.py

from redis_fifo_queue import RedisFIFOQueue
from priority_scheduler_queue import PrioritySchedulerQueue
from sjf_scheduler_queue import SJFQueue
from aging_priority_scheduler_queue import AgingPrioritySchedulerQueue
from weighted_scheduler_queue import WeightedSchedulerQueue

def get_scheduler(scheduler_type: str):

    if scheduler_type == "fifo":
        return RedisFIFOQueue()

    elif scheduler_type == "priority":
        return PrioritySchedulerQueue()

    elif scheduler_type == "sjf":
        return SJFQueue()

    elif scheduler_type == "aging":
        return AgingPrioritySchedulerQueue()

    elif scheduler_type == "weighted":
        return WeightedSchedulerQueue()

    else:
        raise ValueError(
            f"Unknown scheduler: {scheduler_type}"
        )
