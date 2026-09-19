# cluster/ - the REAL stack, scripted end to end

Records the talk's three demos on genuine infrastructure: real Kubernetes (k3s),
the GA Gateway API Inference Extension CRDs, the real llm-d router (EPP + KV-cache
indexer + InferencePool) and real vLLM model servers - the official llm-d guide's
own CPU-sized variant, so it fits a default AWS quota (no GPUs needed) for ~$2.

Everything below runs FROM YOUR MAC. Record your terminal; the scripts stream
clean output from the box.

## Run order (total hands-on time: minutes; waiting: ~20 min in step 1)

```bash
cd cluster
./0_launch_box.sh                      # ~2 min · m7i.4xlarge on CloudFluently
HF_TOKEN=hf_xxx ./1_bootstrap_stack.sh # ~15-25 min unattended · full stack up
./2_rec1_hit.sh                        # REC 1 · cold vs hit + engine counters
./3_rec2_scatter.sh                    # REC 2 · stock Service = the scatter
./4_rec3_heal.sh                       # REC 3 · llm-d EPP = the heal + InferencePool
./9_teardown.sh                        # ALWAYS · terminates the box
```

## What each recording shows
- REC 1 (lever 1): same 3k-token prefix twice against the stack; TTFT collapses
  on the hit, then `vllm:prefix_cache_hits/queries` from the engine itself.
- REC 2 (the bug): three tenants interleaved through a stock Kubernetes Service
  over the same two pods - warm TTFT stays high, tenants keep landing cold.
- REC 3 (lever 2): identical workload through the llm-d router - tenants pin to
  their warm pod, warm TTFT collapses; closes on `kubectl get inferencepool`.

## Notes
- CPU-sized on purpose: routing behaviour is identical to GPU; only absolute
  latencies are bigger (which reads even more dramatically on camera). For the
  GPU version (g5.2xlarge, once quota approves): apply the guide's
  `modelserver/gpu/vllm/base/` overlay in step 1 instead of `cpu/vllm/`.
- The model is the guide's CPU default (Llama-3.2-3B-Instruct - your HF token
  must have Meta-Llama access; most do). Scripts auto-detect the model name.
- KServe layer (optional REC 4): install KServe + Envoy Gateway quickstarts,
  then `kubectl apply -k` github.com/natifridman/kserve-demo (unofficial
  scaffolding; cite official docs) and record `kubectl get llminferenceservice`.
- If anything wedges: `./9_teardown.sh` and start over - the whole thing is
  disposable by design.
