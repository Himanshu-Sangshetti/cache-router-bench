# The Demo Shooting Script
One terminal, font size up, dark theme. Each TAKE = one recording. Everything on
screen is real: the code is the public repo, the cluster is live on AWS.

---

## TAKE 0 · "nothing up my sleeve" (the code) · ~40s

RUN:
```bash
cd ~/Downloads/cache-router-bench && ls cluster/
sed -n '20,40p' cluster/1_bootstrap_stack.sh
```
YOU SEE: the numbered scripts; the bootstrap's middle section - the OFFICIAL
llm-d commands (GAIE CRDs, `helm install` of the router chart, the guide's
kustomize overlay).

SAY: "Everything I am about to show is public - this repo. The setup script is
mostly llm-d's own guide, verbatim: the Inference Extension CRDs, the router
helm chart, their model-server overlay. One box on AWS, about two dollars."

## TAKE 1 · the setup tour · ~90s

RUN:
```bash
cd cluster && ./1b_show_setup.sh
```
YOU SEE, in order - SAY over each:
- `kubectl get nodes` -> "A real Kubernetes cluster - k3s on one AWS box; the
  same YAML runs on EKS or GKE."
- `kubectl get pods` -> "The cast. This pod is llm-d's router, the Endpoint
  Picker - it is subscribed to every model server's KV-cache events over ZMQ,
  it literally keeps the phone book. And these two are real vLLM servers, each
  with its own private KV cache. Private is the whole problem."
- `helm list` -> "Deployed from llm-d's official chart, not hand-rolled."
- `kubectl get inferencepool` -> "And this is the standard: InferencePool, GA,
  from the Gateway API Inference Extension. The router plugs into this."
- the flags dump -> "And the pods run with the exact flags from my slides:
  kv-events-config publishing cache state, block size 64. Nothing custom."

## TAKE 2 · REC 1 · the cache hit (lever 1) · ~2 min

RUN:
```bash
./2_rec1_hit.sh
```
YOU SEE:
```
request 1 · COLD · full prefill     TTFT =   <tens of seconds> ms
request 2 · same prefix · HIT       TTFT =   <~1s> ms   <- prefill skipped
=== the engine's own receipt ===
vllm:prefix_cache_hits{...}   <n>
vllm:prefix_cache_queries{...} <n>
```
SAY: "Same three-thousand-token prefix, twice. Request one: the engine reads
every token - that wait is prefill, this is CPU inference so you really feel
it. Request two, same prefix, new question - near instant. And I don't need
you to trust my stopwatch: these counters are the engine's own. prefix_cache_hits
just jumped. That is lever one, inside one pod."

POINT AT: the two TTFTs, then the hits counter.

## TAKE 3 · REC 2 · the scatter (the bug) · ~3-4 min

RUN:
```bash
./3_rec2_scatter.sh
```
YOU SEE: a `blind` Service created, then three tenants x three rounds:
```
r0 ALPHA   TTFT= <cold>
...
r2 CHARLIE TTFT= <still slow half the time>
warm-mean TTFT: <high> ms
```
SAY: "Now the bug. Same two pods - but in front of them, a stock Kubernetes
Service, the default every one of us runs. Three tenants, interleaved. Watch
the later rounds: they should all be warm by now, but round-robin keeps sending
tenants to the pod that has never seen their prefix. The cache they paid for
sits idle one pod away. And notice - nothing errors. Every request succeeds.
That is why nobody gets paged for this."

POINT AT: a late-round line that is still slow; the warm-mean.

## TAKE 4 · REC 3 · the heal (lever 2) · ~2-3 min

RUN:
```bash
./4_rec3_heal.sh
```
YOU SEE: same workload via the EPP; late rounds all fast; then:
```
warm-mean TTFT: <low> ms
=== the GA resource, on camera ===
NAME                          ...
kubectl get pods -o wide ...
```
SAY: "Identical workload, one change: requests now enter through llm-d's
router. It checks the phone book before choosing - filter to the pods that
hold this prefix, pick the least busy. Same pods, same traffic: warm requests
collapse. Route to the cache, not around it. And it is all standard plumbing -
there is the InferencePool."

POINT AT: warm-mean vs TAKE 3's; the inferencepool line.

## AFTER · always

```bash
./9_teardown.sh     # the box bills $0.81/hr until you do
```

## The honest line (say once, anywhere)
"This box is CPU inference, so the absolute numbers are big - on GPUs the same
routing story plays out in milliseconds; llm-d's published H100 benchmarks show
TTFT p90 going from 135 seconds to 0.26 under load. What you watched is the
mechanism, on infrastructure anyone can reproduce for two dollars from the repo."
