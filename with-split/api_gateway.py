# api_gateway.py

from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum
from datetime import datetime
import uuid

from scheduler_factory import get_scheduler
import time
from adaptive_token_estimator import AdaptiveTokenEstimator

app = FastAPI(title="QoS-Aware GPU Inference API Gateway")
estimator = AdaptiveTokenEstimator()


class PriorityTier(str, Enum):
    premium = "premium"
    standard = "standard"
    batch = "batch"


class SchedulerType(str, Enum):
    fifo = "fifo"
    priority = "priority"
    sjf = "sjf"
    aging = "aging"
    weighted = "weighted"


class InferenceRequest(BaseModel):
    tenant_id: str
    prompt: str
    priority_tier: PriorityTier = PriorityTier.standard
    max_output_tokens: int = 256
    scheduler_type: SchedulerType = SchedulerType.fifo


@app.post("/submit")
def submit_request(request: InferenceRequest):
    request_id = str(uuid.uuid4())

    arrival_time = time.time()
    input_tokens_estimate = len(request.prompt.split())

    estimate = estimator.estimate_budget(
    request.prompt,
    request.priority_tier.value
    )

    estimated_output_tokens = estimate["estimated_output_tokens"]
    total_token_budget = input_tokens_estimate + estimated_output_tokens

    if total_token_budget <= 128:
        job_type = "short"
    elif total_token_budget <= 512:
        job_type = "medium"
    else:
        job_type = "long"
        
    print(
        f"ADMISSION ESTIMATE | "
        f"category={estimate['category']} | "
        f"bias={estimate['bias']:.3f} | "
        f"estimated_output_tokens={estimated_output_tokens} | "
        f"total_token_budget={total_token_budget} | "
        f"job_type={job_type}"
    )        

    scheduler_payload = {
        "request_id": request_id,
        "tenant_id": request.tenant_id,
        "prompt": request.prompt,
        "priority_tier": request.priority_tier.value,
        "scheduler_type": request.scheduler_type.value,
        "arrival_time": arrival_time,
        "input_tokens_estimate": input_tokens_estimate,
        "max_output_tokens": request.max_output_tokens,
        "total_token_budget": total_token_budget,
        "job_type": job_type,
        "status": "queued",
        "workload_category": estimate["category"],
        "estimated_output_tokens": estimated_output_tokens,
        "base_tokens": estimate["base_tokens"],
        "estimation_bias": estimate["bias"],
        "safety_factor": estimate["safety_factor"],
        "input_factor": estimate["input_factor"]
    }

    scheduler = get_scheduler(request.scheduler_type.value)
    scheduler.add_request(scheduler_payload)

    return {
        "message": f"Request received and added to {request.scheduler_type.value} queue",
        "request_id": request_id,
        "scheduler_type": request.scheduler_type.value,
        "job_type": job_type,
        "queue_size": scheduler.queue_size(),
        "status": "queued"
    }


@app.get("/health")
def health_check():
    return {"status": "API Gateway is running"}
