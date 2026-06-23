import json
import time
import redis
from typing import Dict, Optional


class AgingPrioritySchedulerQueue:

    def __init__(self):
        self.client = redis.Redis(host="localhost", port=6379, db=0)

        self.queue_map = {
            "premium": "aging_premium_queue",
            "standard": "aging_standard_queue",
            "batch": "aging_batch_queue"
        }

        self.priority_map = {
            "premium": 1,
            "standard": 2,
            "batch": 3
        }

        self.aging_factor = 0.01

    def add_request(self, request_payload: Dict):
        tier = request_payload.get("priority_tier", "standard")
        queue_name = self.queue_map.get(tier, "aging_standard_queue")

        request_payload["enqueue_time"] = time.time()

        self.client.rpush(
            queue_name,
            json.dumps(request_payload)
        )

    def get_next_request(self) -> Optional[Dict]:
        now = time.time()

        best_item = None
        best_queue = None
        best_score = float("inf")

        for tier, queue_name in self.queue_map.items():
            items = self.client.lrange(queue_name, 0, -1)

            for item in items:
                request_payload = json.loads(item)

                base_priority = self.priority_map.get(tier, 3)
                enqueue_time = request_payload.get("enqueue_time", now)
                waiting_seconds = now - enqueue_time

                aging_score = base_priority - (
                    waiting_seconds * self.aging_factor
                )

                if aging_score < best_score:
                    best_score = aging_score
                    best_item = item
                    best_queue = queue_name

        if best_item is None:
            return None

        self.client.lrem(best_queue, 1, best_item)

        return json.loads(best_item)

    def queue_size(self):
        return sum(
            self.client.llen(queue_name)
            for queue_name in self.queue_map.values()
        )

    def clear(self):
        for queue_name in self.queue_map.values():
            self.client.delete(queue_name)