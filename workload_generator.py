import requests
import random
import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from prompts_dataset import PROMPTS, TOKEN_LIMITS
from scheduler_factory import get_scheduler

API_URL = "http://localhost:8000/submit"

TENANTS = [
    {"tenant_id": "tenant-premium", "priority_tier": "premium"},
    {"tenant_id": "tenant-standard", "priority_tier": "standard"},
    {"tenant_id": "tenant-batch", "priority_tier": "batch"},
]


def create_request(i, scheduler_type="priority", job_type=None):
    tenant = random.choice(TENANTS)

    if job_type is None:
        job_type = random.choices(
            ["short_qa", "summary", "technical", "report"],
            weights=[40, 25, 25, 10],
            k=1
        )[0]

    base_prompt = random.choice(PROMPTS[job_type])

    prompt = (
        f"Request ID {i}. "
        f"Tenant {tenant['tenant_id']}. "
        f"Job type {job_type}. "
        f"{base_prompt}"
    )

    return {
        "tenant_id": tenant["tenant_id"],
        "prompt": prompt,
        "priority_tier": tenant["priority_tier"],
        "max_output_tokens": TOKEN_LIMITS[job_type],
        "scheduler_type": scheduler_type
    }


def send_request(i, scheduler_type, job_type=None):
    payload = create_request(i, scheduler_type, job_type)

    start = time.time()

    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        end = time.time()

        return {
            "request_number": i,
            "status_code": response.status_code,
            "elapsed": round(end - start, 4),
            "payload": payload,
            "response": response.json()
        }

    except Exception as e:
        return {
            "request_number": i,
            "error": str(e),
            "payload": payload
        }


def select_job_type(i):
    if i < 1000:
        return random.choices(
            ["short_qa", "summary", "technical", "report"],
            weights=[40, 25, 25, 10],
            k=1
        )[0]

    return random.choices(
        ["short_qa", "summary", "technical", "report"],
        weights=[10, 20, 40, 30],
        k=1
    )[0]


def run_burst(
    total_requests=3000,
    concurrency=50,
    scheduler_type="priority",
    arrival_delay=True
):
    print(f"Sending {total_requests} requests with concurrency={concurrency}")
    print(f"Scheduler: {scheduler_type}")
    print(f"Arrival delay: {arrival_delay}")

    learning_requests = 1000

    with ThreadPoolExecutor(max_workers=concurrency) as executor:

        # -----------------------------
        # Phase 1: Learning Phase
        # -----------------------------
        print(">>> Starting Learning Phase: first 1000 requests")

        learning_futures = []

        for i in range(learning_requests):
            job_type = select_job_type(i)

            if arrival_delay:
                time.sleep(random.uniform(0.05, 0.15))

            learning_futures.append(
                executor.submit(
                    send_request,
                    i,
                    scheduler_type,
                    job_type
                )
            )

        # Wait until all first 1000 HTTP submissions complete
        for future in as_completed(learning_futures):
            result = future.result()
            print(result)

        print(">>> Learning Phase submissions completed")
        print(">>> Waiting for learning queue to drain...")

        scheduler = get_scheduler(scheduler_type)

        while True:
            qsize = scheduler.queue_size()

            if qsize == 0:
                break

            print(f"Learning queue size: {qsize}")
            time.sleep(2)

        print(">>> Learning queue drained")
        print(">>> Waiting for final in-flight batch to finish...")
        time.sleep(15)

        print(">>> Starting Stress Phase: remaining 2000 requests")

        # -----------------------------
        # Phase 2: Stress Phase
        # -----------------------------
        stress_futures = []

        for i in range(learning_requests, total_requests):
            job_type = select_job_type(i)

            if arrival_delay:
                time.sleep(random.uniform(0.005, 0.03))

            stress_futures.append(
                executor.submit(
                    send_request,
                    i,
                    scheduler_type,
                    job_type
                )
            )

        for future in as_completed(stress_futures):
            result = future.result()
            print(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scheduler",
        default="priority",
        choices=["fifo", "priority", "sjf", "aging", "weighted"]
    )

    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--arrival-delay", action="store_true")

    args = parser.parse_args()

    run_burst(
        total_requests=args.requests,
        concurrency=args.concurrency,
        scheduler_type=args.scheduler,
        arrival_delay=args.arrival_delay
    )