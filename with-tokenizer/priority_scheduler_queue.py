import json
import time
import redis
from typing import Dict, Optional


class PrioritySchedulerQueue:

    def __init__(self):
        self.client = redis.Redis(host="localhost", port=6379, db=0)

        self.queue_map = {
            "premium": "priority_premium_queue",
            "standard": "priority_standard_queue",
            "batch": "priority_batch_queue"
        }

        self.priority_order = [
            "premium",
            "standard",
            "batch"
        ]

    def add_request(self, request_payload: Dict):
        tier = request_payload.get("priority_tier", "standard")
        queue_name = self.queue_map.get(tier, "priority_standard_queue")

        self.client.rpush(
            queue_name,
            json.dumps(request_payload)
        )

    def get_next_request(self) -> Optional[Dict]:

        # Strict priority:
        # Always check premium first, then standard, then batch.
        for tier in self.priority_order:
            queue_name = self.queue_map[tier]

            item = self.client.lpop(queue_name)

            if item:
                return json.loads(item)

        return None

    def queue_size(self):
        return sum(
            self.client.llen(queue_name)
            for queue_name in self.queue_map.values()
        )

    def clear(self):
        for queue_name in self.queue_map.values():
            self.client.delete(queue_name)