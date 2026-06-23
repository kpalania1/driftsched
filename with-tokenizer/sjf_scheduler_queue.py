import json
import redis
import time
from typing import Dict, Optional


class SJFQueue:

    def __init__(self):
        self.client = redis.Redis(host="localhost", port=6379, db=0)

        self.queue_map = {
            "premium": "sjf_premium_queue",
            "standard": "sjf_standard_queue",
            "batch": "sjf_batch_queue"
        }

    def add_request(self, request_payload: Dict):
        tier = request_payload.get("priority_tier", "standard")
        queue_name = self.queue_map.get(tier, "sjf_standard_queue")

        estimated_size = request_payload.get("total_token_budget", 999999)
        arrival_time = time.time()

        score = (estimated_size * 1_000_000_000) + arrival_time

        self.client.zadd(
            queue_name,
            {json.dumps(request_payload): score}
        )

    def get_next_request(self) -> Optional[Dict]:

        candidates = []

        for queue_name in self.queue_map.values():
            item = self.client.zrange(queue_name, 0, 0)

            if item:
                payload = json.loads(item[0])
                candidates.append(
                    (
                        payload.get("total_token_budget", 999999),
                        payload.get("arrival_time", time.time()),
                        queue_name,
                        item[0]
                    )
                )

        if not candidates:
            return None

        # Pick shortest estimated job across all tenant queues
        _, _, selected_queue, selected_item = min(
            candidates,
            key=lambda x: (x[0], x[1])
        )

        self.client.zrem(selected_queue, selected_item)

        return json.loads(selected_item)

    def queue_size(self):
        return sum(
            self.client.zcard(queue_name)
            for queue_name in self.queue_map.values()
        )

    def clear(self):
        for queue_name in self.queue_map.values():
            self.client.delete(queue_name)