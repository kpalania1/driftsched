# gpu_inference_worker.py

import time
from typing import Dict, List

from vllm import LLM, SamplingParams


class GPUInferenceWorker:

    def __init__(self):

        self.llm = LLM(
            model="Qwen/Qwen1.5-1.8B-Chat",
            tokenizer="Qwen/Qwen1.5-1.8B-Chat",
            tokenizer_mode="auto",
            dtype="float16",
            gpu_memory_utilization=0.70,
            max_model_len=2048,
            enforce_eager=True,
            trust_remote_code=True
        )

    def process_batch(self, request_batch: List[Dict]):

        prompts = [
            request_payload["prompt"]
            for request_payload in request_batch
        ]

        sampling_params_list = [
            SamplingParams(
                temperature=0.7,
                max_tokens=request_payload["max_output_tokens"]
            )
            for request_payload in request_batch
        ]

        print("\n==============================")
        print("GPU MICRO-BATCH")
        print("==============================")
        print(f"Batch size: {len(request_batch)}")

        for request_payload in request_batch:
            print(
                f"Request ID: {request_payload['request_id']} | "
                f"Tenant: {request_payload['tenant_id']} | "
                f"Priority: {request_payload['priority_tier']} | "
                f"Job Type: {request_payload['job_type']} | "
                f"Category: {request_payload.get('workload_category')}"
            )

        print("==============================\n")

        start_time = time.time()

        outputs = self.llm.generate(
            prompts,
            sampling_params_list
        )

        end_time = time.time()

        batch_latency = end_time - start_time

        results = []

        for request_payload, output in zip(request_batch, outputs):

            generated_text = output.outputs[0].text

            generated_tokens = len(
                generated_text.split()
            )

            metrics = {
                "request_id": request_payload["request_id"],
                "job_type": request_payload["job_type"],
                "priority_tier": request_payload["priority_tier"],
                "latency_seconds": batch_latency,
                "generated_tokens": generated_tokens,
                "status": "completed"
            }

            results.append({
                "generated_text": generated_text,
                "metrics": metrics
            })

        return results