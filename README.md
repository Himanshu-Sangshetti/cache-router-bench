# cache-router-bench

**KV-cache-aware routing for LLM inference, measured two ways: on your laptop in
four minutes, and on a real Kubernetes + llm-d stack for ~$2.**

Companion repo for the KCD Gujarat 2026 talk *"Scaling LLM Inference on Kubernetes
with KV-Cache-Aware Routing"* — but built to be useful standalone.

## The idea in three sentences

LLM serving has one expensive step that gets repeated by accident: **prefill**, where
the GPU reads your whole prompt and builds the KV cache. Production traffic mostly
repeats the same prompt *beginnings* (system prompts, tool definitions, documents), so
engines like vLLM reuse the cache within a worker — but the moment you scale to N
replicas behind a normal load balancer, requests scatter and hit their own cache only
~1/N of the time. The fix is **routing on cache state** (what [llm-d](https://llm-d.ai)
does on Kubernetes), and this repo lets you measure the whole story yourself.

## Quick start · the laptop benchmark (4 minutes, no GPU)

Real inference (llama.cpp + any small GGUF model), no simulation. The smoking gun in
every result is `prompt_n` — the server's own count of prompt tokens it actually
computed (thousands on a miss, single digits on a hit).

```bash
brew install llama.cpp        # or your platform's equivalent
# point MODEL at any GGUF you have (defaults to an ollama blob path):
MODEL=/path/to/model.gguf python3 bench.py
```

Four experiments, one run:

| # | question | result on an M-series MacBook (3.7k-token prefix) |
|---|---|---|
| E1 | what is one cache hit worth? | cold 3,873 ms → hit **70 ms (55×)**; same request to a fresh replica: full price again |
| E2 | routing policy, all else fixed | round-robin 2,435 ms / 50% hits / 12,007 tokens computed → prefix-affinity **162 ms / 100% / 45 tokens** |
| E3 | control: unique prefixes | both policies do identical work — **if nothing repeats, routing cannot help** |
| E4 | kill the pinned replica | one cold request on the survivor, then warm again — caches are state you can afford to lose |

## The real stack · `cluster/` (~$2, no GPU quota needed)

Scripts that stand up the **genuine components** on one cloud VM: k3s Kubernetes, the
GA [Gateway API Inference Extension](https://gateway-api-inference-extension.sigs.k8s.io/)
CRDs, the real [llm-d router](https://github.com/llm-d/llm-d) (Endpoint Picker +
KV-cache indexer + InferencePool) and vLLM model servers publishing real KV events —
using llm-d's own official guide, CPU-sized so it fits a default AWS quota.

```bash
cd cluster
./0_launch_box.sh                 # one m7i.4xlarge on your AWS account
./1_bootstrap_stack.sh            # the whole stack, unattended (~20 min)
./2_rec1_hit.sh                   # cold vs hit + the engine's own counters
./3_rec2_scatter.sh               # stock k8s Service = the scatter
./4_rec3_heal.sh                  # llm-d EPP = the heal + `kubectl get inferencepool`
./9_teardown.sh                   # always
```

AWS-specific bits are only in `0_launch_box.sh` — any Ubuntu box with 16 vCPUs works
for the rest. See [`cluster/README.md`](cluster/README.md).

## Also here

- [`OPS_CHECKLIST.md`](OPS_CHECKLIST.md) — what to check on *your* cluster this week:
  the two vLLM hit-rate counters, the diagnostic signature of the scatter problem,
  and when each lever (caching / routing / P/D disaggregation) is worth it.
- `results.json` / `results.csv` — a full measured run of the laptop benchmark.

## Honest scope

- The laptop bench uses llama.cpp slot caches and a hash router as stand-ins for
  vLLM APC and llm-d's EPP: same mechanism, small scale, clearly labeled.
- The `cluster/` stack is the real thing, CI-sized (CPU): routing behavior is
  identical to GPU deployments; absolute latencies are not.
- Production-scale numbers belong to the official llm-d benchmarks:
  [the four-strategy blog](https://llm-d.ai/blog/kvcache-wins-you-can-see) and
  [the 16×H100 results](https://github.com/llm-d/llm-d/blob/main/guides/precise-prefix-cache-routing/benchmark-results/vllm-qwen3-32b-h100.md)
  (+113% throughput, TTFT p50 54.6 s → 0.19 s vs a plain Service).

## Sources (all first-party)

[vLLM: Automatic Prefix Caching](https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/) ·
[vLLM: metrics](https://docs.vllm.ai/en/latest/design/metrics.html) ·
[llm-d: precise prefix-cache routing guide](https://github.com/llm-d/llm-d/tree/main/guides/precise-prefix-cache-routing) ·
[llm-d: P/D disaggregation](https://github.com/llm-d/llm-d/tree/main/guides/pd-disaggregation) ·
[Gateway API Inference Extension](https://gateway-api-inference-extension.sigs.k8s.io/) ·
[KServe + llm-d](https://kserve.github.io/website/blog/cloud-native-ai-inference-kserve-llm-d)

## License

MIT — see [LICENSE](LICENSE).
