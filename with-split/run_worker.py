# run_worker.py

import time
import glob
import sys
import csv
import os
import uuid
from datetime import datetime

from scheduler_factory import get_scheduler
from gpu_inference_worker import GPUInferenceWorker
from adaptive_token_estimator import AdaptiveTokenEstimator


scheduler_type = sys.argv[1]
scheduler = get_scheduler(scheduler_type)

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", 8))
BATCH_WAIT_SECONDS = float(os.environ.get("BATCH_WAIT_SECONDS", 0.05))

if hasattr(scheduler, "clear"):
    scheduler.clear()
else:
    scheduler.client.delete(scheduler.queue_name)

worker = GPUInferenceWorker()
estimator = AdaptiveTokenEstimator()

estimator.client.delete("token_bias:short_qa")
estimator.client.delete("token_bias:summary")
estimator.client.delete("token_bias:technical")
estimator.client.delete("token_bias:report")

existing = glob.glob(f"metrics_{scheduler_type}_*.csv")
run_number = len(existing) + 1

METRICS_FILE = os.environ.get(
    "METRICS_FILE",
    f"metrics_{scheduler_type}.csv"
)

if os.path.exists(METRICS_FILE):
    os.remove(METRICS_FILE)


def write_metrics(metrics):
    file_exists = os.path.exists(METRICS_FILE)

    with open(METRICS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "scheduler_type",
                "request_id",
                "tenant_id",
                "job_type",
                "workload_category",
                "priority_tier",
                "batch_id",
                "batch_size",
                "total_token_budget",
                "estimated_output_tokens",
                "max_output_tokens",
                "generated_tokens",
                "queue_enter_time",
                "worker_start_time",
                "worker_finish_time",
                "queue_wait_seconds",
                "inference_seconds",
                "end_to_end_seconds",
                "latency_seconds",
                "status",
                "feedback_old_bias",
                "feedback_measured_bias",
                "feedback_new_bias",
                "estimation_bias",
                "base_tokens",
                "safety_factor",
                "input_factor"
            ]
        )

        if not file_exists:
            writer.writeheader()

        metrics["timestamp"] = datetime.utcnow().isoformat()
        writer.writerow(metrics)


def get_request_batch():
    batch = []

    first_request = scheduler.get_next_request()

    if first_request is None:
        return batch

    batch.append(first_request)

    batch_start_time = time.time()

    while len(batch) < BATCH_SIZE:
        request_payload = scheduler.get_next_request()

        if request_payload is not None:
            batch.append(request_payload)
            continue

        if time.time() - batch_start_time >= BATCH_WAIT_SECONDS:
            break

        time.sleep(0.005)

    return batch


def run():
    print(f"{scheduler_type.upper()} Worker Started...")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Batch wait seconds: {BATCH_WAIT_SECONDS}")

    while True:
        request_batch = get_request_batch()

        if not request_batch:
            time.sleep(1)
            continue

        batch_id = str(uuid.uuid4())

        print(
            f"Processing batch {batch_id} "
            f"with {len(request_batch)} requests"
        )

        worker_start_time = time.time()

        batch_results = worker.process_batch(request_batch)

        worker_finish_time = time.time()

        for request_payload, result in zip(request_batch, batch_results):

            metrics = result["metrics"]

            queue_enter_time = float(request_payload["arrival_time"])

            metrics["scheduler_type"] = scheduler_type
            metrics["tenant_id"] = request_payload["tenant_id"]
            metrics["workload_category"] = request_payload.get("workload_category")
            metrics["priority_tier"] = request_payload["priority_tier"]

            metrics["batch_id"] = batch_id
            metrics["batch_size"] = len(request_batch)

            metrics["total_token_budget"] = request_payload["total_token_budget"]
            metrics["estimated_output_tokens"] = request_payload.get("estimated_output_tokens")
            metrics["max_output_tokens"] = request_payload["max_output_tokens"]

            metrics["queue_enter_time"] = queue_enter_time
            metrics["worker_start_time"] = worker_start_time
            metrics["worker_finish_time"] = worker_finish_time

            metrics["queue_wait_seconds"] = worker_start_time - queue_enter_time
            metrics["inference_seconds"] = worker_finish_time - worker_start_time
            metrics["end_to_end_seconds"] = worker_finish_time - queue_enter_time
            metrics["latency_seconds"] = worker_finish_time - worker_start_time

            category = request_payload.get("workload_category")
            actual_tokens = metrics["generated_tokens"]

            feedback = None

            if category:
                feedback = estimator.apply_feedback(
                    category,
                    actual_tokens
                )

            metrics["feedback_old_bias"] = feedback["old_bias"] if feedback else None
            metrics["feedback_new_bias"] = feedback["new_bias"] if feedback else None
            metrics["feedback_measured_bias"] = feedback["measured_bias"] if feedback else None

            metrics["estimation_bias"] = request_payload.get("estimation_bias")
            metrics["base_tokens"] = request_payload.get("base_tokens")
            metrics["safety_factor"] = request_payload.get("safety_factor")
            metrics["input_factor"] = request_payload.get("input_factor")

            print(metrics)
            write_metrics(metrics)


if __name__ == "__main__":
    run()