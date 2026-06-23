#!/bin/bash

# =========================================================
# DriftSched Experimental Evaluation Framework
# Executes multi-tenant LLM scheduling experiments
# across FIFO, Priority, SJF, Weighted, and Aging
# schedulers while collecting latency, queue, and
# GPU telemetry metrics.
# =========================================================
BIAS_MODE=${BIAS_MODE:-on}
export BIAS_MODE

echo "Bias Mode    : $BIAS_MODE"

REQUESTS=3000
CONCURRENCY=50
RUNS=3

BATCH_SIZE=32
BATCH_WAIT_SECONDS=0.01

SCHEDULERS=("fifo" "priority" "sjf" "weighted" "aging")

BASE_DIR="experiment_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BASE_DIR"

export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "================================================="
echo "QoS Scheduling Experiment Suite"
echo "================================================="
echo "Requests     : $REQUESTS"
echo "Concurrency  : $CONCURRENCY"
echo "Runs         : $RUNS"
echo "Output Dir   : $BASE_DIR"
echo "================================================="

for SCHEDULER in "${SCHEDULERS[@]}"
do
    echo ""
    echo "#################################################"
    echo "Scheduler: $SCHEDULER"
    echo "#################################################"

    for ((RUN=1; RUN<=RUNS; RUN++))
    do
        echo ""
        echo "================================================="
        echo "Starting Run $RUN for Scheduler $SCHEDULER"
        echo "================================================="

        redis-cli FLUSHALL > /dev/null 2>&1

        RUN_DIR="${BASE_DIR}/${SCHEDULER}_run${RUN}"
        mkdir -p "$RUN_DIR"

        TELEMETRY_FILE="${RUN_DIR}/telemetry.csv"
        WORKER_LOG="${RUN_DIR}/worker.log"
        GENERATOR_LOG="${RUN_DIR}/generator.log"
        METRICS_FILE="${RUN_DIR}/metrics.csv"

        export METRICS_FILE

        EXPERIMENT_START=$(date +%s)

        echo "Starting telemetry logger..."

        nvidia-smi \
          --query-gpu=timestamp,index,name,temperature.gpu,power.draw,pstate,clocks.sm,clocks.mem,utilization.gpu,utilization.memory,memory.used,memory.total \
          --format=csv,nounits \
          -lms 200 > "$TELEMETRY_FILE" &

        TELEMETRY_PID=$!

		QUEUE_MONITOR_FILE="${RUN_DIR}/queue_depth.csv"

		echo "elapsed_seconds,premium_queue,standard_queue,batch_queue,total_queue_size" > "$QUEUE_MONITOR_FILE"

		echo "Starting Redis queue monitor..."

		(
		START_TIME=$(date +%s)

		while true
		do
			CURRENT_TIME=$(date +%s)
			ELAPSED=$((CURRENT_TIME - START_TIME))

			if [ "$SCHEDULER" = "fifo" ]; then
				PREMIUM=$(redis-cli LLEN fifo_premium_queue 2>/dev/null)
				STANDARD=$(redis-cli LLEN fifo_standard_queue 2>/dev/null)
				BATCH=$(redis-cli LLEN fifo_batch_queue 2>/dev/null)
				QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))
			elif [ "$SCHEDULER" = "priority" ]; then
				PREMIUM=$(redis-cli LLEN priority_premium_queue 2>/dev/null)
				STANDARD=$(redis-cli LLEN priority_standard_queue 2>/dev/null)
				BATCH=$(redis-cli LLEN priority_batch_queue 2>/dev/null)
				QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))
			elif [ "$SCHEDULER" = "sjf" ]; then
				PREMIUM=$(redis-cli ZCARD sjf_premium_queue 2>/dev/null)
				STANDARD=$(redis-cli ZCARD sjf_standard_queue 2>/dev/null)
				BATCH=$(redis-cli ZCARD sjf_batch_queue 2>/dev/null)
				QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))
			elif [ "$SCHEDULER" = "aging" ]; then
                PREMIUM=$(redis-cli LLEN aging_premium_queue 2>/dev/null)
				STANDARD=$(redis-cli LLEN aging_standard_queue 2>/dev/null)
				BATCH=$(redis-cli LLEN aging_batch_queue 2>/dev/null)
				QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))
			elif [ "$SCHEDULER" = "weighted" ]; then
				PREMIUM=$(redis-cli LLEN weighted_premium_queue 2>/dev/null)
				STANDARD=$(redis-cli LLEN weighted_standard_queue 2>/dev/null)
				BATCH=$(redis-cli LLEN weighted_batch_queue 2>/dev/null)
				QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))
			fi

			echo "$ELAPSED,$PREMIUM,$STANDARD,$BATCH,$QUEUE_SIZE" >> "$QUEUE_MONITOR_FILE"
			sleep 1
		done
		) &

		QUEUE_MONITOR_PID=$!

        echo "Starting worker..."

		export BATCH_SIZE
		export BATCH_WAIT_SECONDS
		
        python3 run_worker.py "$SCHEDULER" > "$WORKER_LOG" 2>&1 &
        WORKER_PID=$!

        sleep 8

        echo "Starting workload generator..."
		
		echo "Batch Size   : $BATCH_SIZE"
		echo "Batch Wait   : $BATCH_WAIT_SECONDS"

        python3 workload_generator.py \
          --scheduler "$SCHEDULER" \
          --requests "$REQUESTS" \
          --concurrency "$CONCURRENCY" \
		  --arrival-delay \
          | tee "$GENERATOR_LOG"

        echo ""
        echo "Waiting for queue drain..."

        while true
        do
            if [ "$SCHEDULER" = "fifo" ]; then
				PREMIUM=$(redis-cli LLEN fifo_premium_queue 2>/dev/null)
				STANDARD=$(redis-cli LLEN fifo_standard_queue 2>/dev/null)
				BATCH=$(redis-cli LLEN fifo_batch_queue 2>/dev/null)
				QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))
				
            elif [ "$SCHEDULER" = "priority" ]; then
				PREMIUM=$(redis-cli LLEN priority_premium_queue 2>/dev/null)
				STANDARD=$(redis-cli LLEN priority_standard_queue 2>/dev/null)
				BATCH=$(redis-cli LLEN priority_batch_queue 2>/dev/null)
				QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))

            elif [ "$SCHEDULER" = "sjf" ]; then
				PREMIUM=$(redis-cli ZCARD sjf_premium_queue 2>/dev/null)
				STANDARD=$(redis-cli ZCARD sjf_standard_queue 2>/dev/null)
				BATCH=$(redis-cli ZCARD sjf_batch_queue 2>/dev/null)
				QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))

            elif [ "$SCHEDULER" = "aging" ]; then
                PREMIUM=$(redis-cli LLEN aging_premium_queue 2>/dev/null)
				STANDARD=$(redis-cli LLEN aging_standard_queue 2>/dev/null)
				BATCH=$(redis-cli LLEN aging_batch_queue 2>/dev/null)
				QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))

            elif [ "$SCHEDULER" = "weighted" ]; then
                PREMIUM=$(redis-cli LLEN weighted_premium_queue 2>/dev/null)
                STANDARD=$(redis-cli LLEN weighted_standard_queue 2>/dev/null)
                BATCH=$(redis-cli LLEN weighted_batch_queue 2>/dev/null)
                QUEUE_SIZE=$((PREMIUM + STANDARD + BATCH))

            else
                echo "Unknown scheduler: $SCHEDULER"
                exit 1
            fi

            echo "Remaining Queue Size: $QUEUE_SIZE"

            if [ "$QUEUE_SIZE" -eq 0 ]; then
                break
            fi

            sleep 2
        done

        echo ""
        echo "Waiting for final in-flight request..."
        sleep 10

        echo "Stopping worker and telemetry..."

        kill "$WORKER_PID" 2>/dev/null || true
        kill "$TELEMETRY_PID" 2>/dev/null || true
		kill "$QUEUE_MONITOR_PID" 2>/dev/null || true

        wait "$WORKER_PID" 2>/dev/null || true
        wait "$TELEMETRY_PID" 2>/dev/null || true
		wait "$QUEUE_MONITOR_PID" 2>/dev/null || true

        redis-cli FLUSHALL > /dev/null 2>&1

        EXPERIMENT_END=$(date +%s)
        TOTAL_RUNTIME=$((EXPERIMENT_END - EXPERIMENT_START))

        echo ""
        echo "================================================="
        echo "Run Completed"
        echo "================================================="
        echo "Scheduler     : $SCHEDULER"
        echo "Run           : $RUN"
        echo "Runtime       : ${TOTAL_RUNTIME}s"
        echo "Results Dir   : $RUN_DIR"
        echo "Metrics File  : $METRICS_FILE"
        echo "================================================="

        echo ""
        echo "Cooling GPU before next run..."
        sleep 60

    done
done

echo ""
echo "================================================="
echo "ALL EXPERIMENTS COMPLETED"
echo "================================================="
