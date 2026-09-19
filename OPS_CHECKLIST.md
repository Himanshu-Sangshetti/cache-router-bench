# OPS_CHECKLIST - KV-cache routing, on YOUR cluster this week

The leave-behind from "Scaling LLM Inference: KV-Cache-Aware Routing" (KCD Gujarat 2026).
Work through it top to bottom; each step tells you whether the next one applies.

## 1 · Measure your prefix-cache hit rate (30 min)

vLLM exports Prometheus metrics per pod. The two that matter:

```
vllm:prefix_cache_queries      # counter: prefix cache queries
vllm:prefix_cache_hits         # counter: prefix cache hits
```

hit rate = `rate(vllm:prefix_cache_hits[5m]) / rate(vllm:prefix_cache_queries[5m])`
(the counters are the official interface; compute the rate in PromQL). Check it per pod,
not averaged. Also confirm caching is on
(it is by default in vLLM V1; the engine arg is `enable_prefix_caching`).

- Hit rate high (>60%) and TTFT fine -> you are done. Enjoy.
- Hit rate high INSIDE each pod but end-to-end TTFT bad and you run multiple replicas ->
  you likely have the scatter problem. Continue.
- Hit rate low everywhere -> step 2 first: does your traffic actually share prefixes?

## 2 · Know your workload (30 min)

Sample 100 real prompts. How many share their first 1-2k tokens (system prompt, tool
definitions, RAG boilerplate, chat history)?

- Most share -> prefix reuse is worth chasing. Continue.
- Almost none share -> STOP. Cache-aware routing cannot help you (my control experiment
  and the vLLM docs both say so). Spend your week elsewhere.

## 3 · Look at what your load balancer actually does (15 min)

A stock `Service` (round-robin / random) and most ingresses are cache-blind by
definition. If that is what fronts your vLLM pods and you passed steps 1-2, every
follow-up request has roughly a 1/N chance of landing on its warm pod.

## 4 · Pick your row

| Your situation | Do this |
|---|---|
| one replica, shared prefixes | nothing - APC already covers you |
| many replicas, shared prefixes | **KV-cache-aware routing** (this row is most teams) |
| huge scale, long inputs, RDMA | P/D disaggregation (llm-d well-lit path) |
| no shared prefixes | none of it - do not add complexity |

## 5 · Deploy cache-aware routing (the llm-d way)

Follow the official guide, not a blog rewrite of it:
https://github.com/llm-d/llm-d/blob/main/guides/precise-prefix-cache-routing/README.md

The pieces, so you can review the PR intelligently:
- each vLLM pod: `--kv-events-config` publishing over ZMQ (`--prefix-caching-hash-algo sha256_cbor_64bit`)
- the EPP (Endpoint Picker) with `kvEventsConfig.discoverPods: true`; keep the EPP single-replica
- a Gateway that supports the Inference Extension (Envoy Gateway, GKE, Istio, kgateway, NGINX)
- an `InferencePool` (v1, GA) selecting your pods

Approximate mode (no KV events, hash-based) is the low-friction start; precise mode is
the full win. The four-strategy numbers: https://llm-d.ai/blog/kvcache-wins-you-can-see

## 6 · Verify it worked

- cache-hit rate per pod goes UP and TTFT p90 collapses on shared-prefix traffic
  (in llm-d's benchmark: 135s -> 0.26s p90; on my laptop: 2,435ms -> 162ms warm-mean)
- watch ITL: a ~20% rise is the expected trade; renegotiate thresholds if it breaks your SLO
- kill a pod: traffic should fail over with ONE cold request per tenant, then re-warm
  (my E4: 73ms warm -> kill -> 4,073ms once -> 108ms warm again)

## 7 · Only then consider P/D disaggregation

Long inputs (10k+ tokens), big models, RDMA-class network. Start here:
https://github.com/llm-d/llm-d/blob/main/guides/pd-disaggregation/README.md

---
Reproduce my laptop numbers: `python3 bench.py` in this folder (needs llama.cpp + any
GGUF model; see README). Every other number in the talk is from the official sources above.
