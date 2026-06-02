import json
import redis
from typing import Dict, Optional


class RedisFIFOQueue:

    def __init__(self):
        self.client = redis.Redis(host="localhost", port=6379, db=0)

        self.queue_map = {
            "premium": "fifo_premium_queue",
            "standard": "fifo_standard_queue",
            "batch": "fifo_batch_queue"
        }

    def add_request(self, request_payload: Dict):

        tier = request_payload.get(
            "priority_tier",
            "standard"
        )

        queue_name = self.queue_map.get(
            tier,
            "fifo_standard_queue"
        )

        self.client.rpush(
            queue_name,
            json.dumps(request_payload)
        )

    def get_next_request(self) -> Optional[Dict]:

        candidates = []

        # Look at oldest request from each queue
        for queue_name in self.queue_map.values():

            item = self.client.lindex(
                queue_name,
                0
            )

            if item:
                payload = json.loads(item)

                candidates.append(
                    (
                        payload["arrival_time"],
                        queue_name,
                        item
                    )
                )

        if not candidates:
            return None

        # Pick globally oldest request
        _, selected_queue, selected_item = min(
            candidates,
            key=lambda x: x[0]
        )

        self.client.lpop(selected_queue)

        return json.loads(selected_item)

    def queue_size(self):

        return sum(
            self.client.llen(queue_name)
            for queue_name in self.queue_map.values()
        )

    def clear(self):

        for queue_name in self.queue_map.values():
            self.client.delete(queue_name)