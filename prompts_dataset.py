# prompts_dataset_generator.py
TOPICS = [
    "DNS","BGP","OSPF","MPLS","VPN","SD-WAN","Kubernetes","Docker","AWS","Azure",
    "Kafka","Redis","PostgreSQL","MongoDB","API Gateway","Load Balancing","JWT","OAuth",
    "TLS","LLM Inference","TensorRT","CUDA","GPU Scheduling","Vector Databases","RAG",
    "Microservices","Service Mesh","Observability","CI/CD","Zero Trust",
    "Cloud Security","Network Security","Firewalls","IDS/IPS","SRE","Autoscaling",
    "Distributed Tracing","Rate Limiting","Caching","CDN","Data Pipelines",
    "Event Streaming","GPU Memory Management","KV Cache","PagedAttention",
    "Continuous Batching","Model Quantization","Inference Optimization",
    "Multi-Tenant Systems","Queue Scheduling","Token Estimation","Embeddings",
    "Serverless","Edge Computing","Terraform","Ansible","Prometheus","Grafana","OpenTelemetry"
]

SHORT_QA_TEMPLATES = [
    "What is {topic} and why is it important?",
    "How does {topic} work?",
    "What problem does {topic} solve?",
    "When should {topic} be used?",
    "What are the benefits of {topic}?"
]

SUMMARY_TEMPLATES = [
    "Summarize {topic} architecture and key components.",
    "Summarize the operational benefits of {topic}.",
    "Summarize security considerations for {topic}.",
    "Summarize scalability challenges in {topic}.",
    "Summarize best practices for implementing {topic}."
]

TECHNICAL_TEMPLATES = [
    "Explain the internal architecture of {topic}.",
    "Explain performance tradeoffs associated with {topic}.",
    "Explain implementation details of {topic}.",
    "Explain bottlenecks commonly observed in {topic}.",
    "Explain monitoring and observability requirements for {topic}."
]

REPORT_TEMPLATES = [
    "Write a detailed report on {topic}, including architecture, performance, scalability, security, and operational considerations.",
    "Write a comprehensive analysis of {topic} deployment strategies and best practices.",
    "Write a report comparing different approaches to {topic}.",
    "Write a report discussing reliability, resilience, and risk management for {topic}.",
    "Write a report evaluating future trends and innovations related to {topic}."
]

PROMPTS = {"short_qa": [], "summary": [], "technical": [], "report": []}

for topic in TOPICS:
    for t in SHORT_QA_TEMPLATES:
        PROMPTS["short_qa"].append(t.format(topic=topic))
    for t in SUMMARY_TEMPLATES:
        PROMPTS["summary"].append(t.format(topic=topic))
    for t in TECHNICAL_TEMPLATES:
        PROMPTS["technical"].append(t.format(topic=topic))
    for t in REPORT_TEMPLATES:
        PROMPTS["report"].append(t.format(topic=topic))


TOKEN_LIMITS = {
    "short_qa": 64,
    "summary": 256,
    "technical": 384,
    "report": 512
}

if __name__ == "__main__":
    print(f"Short QA : {len(PROMPTS['short_qa'])}")
    print(f"Summary  : {len(PROMPTS['summary'])}")
    print(f"Technical: {len(PROMPTS['technical'])}")
    print(f"Report   : {len(PROMPTS['report'])}")
    print(f"Total    : {sum(len(v) for v in PROMPTS.values())}")