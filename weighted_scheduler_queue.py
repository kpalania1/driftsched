import json
import redis
from typing import Dict, Optional


class WeightedSchedulerQueue:
    def __init__(self):
        self.client = redis.Redis(host="localhost", port=6379, db=0)

        self.queue_map = {
            "premium": "weighted_premium_queue",
            "standard": "weighted_standard_queue",
            "batch": "weighted_batch_queue"
        }

        # 50 / 30 / 20 scheduling ratio
        self.schedule_cycle = [
            "premium", "premium", "premium", "premium", "premium",
            "standard", "standard", "standard",
            "batch", "batch"
        ]

        self.pointer_key = "weighted_scheduler_pointer"

    def add_request(self, request_payload: Dict):
        priority_tier = request_payload.get("priority_tier", "batch")
        queue_name = self.queue_map.get(priority_tier, "weighted_batch_queue")

        self.client.rpush(queue_name, json.dumps(request_payload))

    def get_next_request(self) -> Optional[Dict]:
        cycle_length = len(self.schedule_cycle)

        start_pointer = int(self.client.get(self.pointer_key) or 0)

        for offset in range(cycle_length):
            pointer = (start_pointer + offset) % cycle_length
            tier = self.schedule_cycle[pointer]
            queue_name = self.queue_map[tier]

            item = self.client.lpop(queue_name)

            if item:
                next_pointer = (pointer + 1) % cycle_length
                self.client.set(self.pointer_key, next_pointer)
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

        self.client.delete(self.pointer_key)
