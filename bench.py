#!/usr/bin/env python3
"""cache-router-bench: real KV-cache routing experiments on llama.cpp llama-server.

Four experiments, all REAL inference (llama3.1-8B Q4, Metal), no simulation:
  E1 reuse    - prefix cache hit vs miss on one worker (TTFT + prompt_n)
  E2 routing  - round-robin vs prefix-affinity across 2 replicas, 3 tenants
  E3 control  - unique-prefix workload: routing policy should NOT matter (honesty)
  E4 failover - kill the pinned replica; affinity recovers after one cold request

The smoking gun in every row is `prompt_n` from the server's own `timings`:
prompt tokens actually evaluated (thousands on a miss, ~a dozen on a hit).

Usage:  python3 bench.py [e1 e2 e3 e4]      (default: all)
Writes: results.json + results.csv next to this file.
"""
import json, os, signal, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).parent
MODEL = os.environ.get("MODEL",
    "/Users/hims/.ollama/models/blobs/sha256-667b0c1932bc6ffc593ed1d03f895bf2dc8dc6df21db3042284a6f4416b06a29")
PORTS = [8081, 8082]
ROWS = []   # (exp, policy, label, port, ttft_ms, prompt_n)

# ---------------- server management ----------------
PROCS = {}

def start(port, np=2, ctx=None):
    ctx = ctx or np * 8192
    log = open(HERE / f"server_{port}.log", "w")
    PROCS[port] = subprocess.Popen(
        ["llama-server", "-m", MODEL, "--port", str(port), "-c", str(ctx),
         "-np", str(np), "-ngl", "99", "--cache-reuse", "256"],
        stdout=log, stderr=log)
    for _ in range(120):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                if b"ok" in r.read(): return
        except Exception: time.sleep(2)
    raise RuntimeError(f"replica :{port} did not come up")

def stop(port=None):
    for p in ([port] if port else list(PROCS)):
        if p in PROCS:
            PROCS[p].terminate()
            try: PROCS[p].wait(10)
            except subprocess.TimeoutExpired: PROCS[p].kill()
            del PROCS[p]
    time.sleep(1)

def fresh(np=2):
    stop(); [start(p, np) for p in PORTS]

# ---------------- workload ----------------
def build_prefix(tag, target_words=2600):
    para = (f"You are the dedicated copilot for tenant {tag}. Follow the {tag} runbook. "
            f"Escalate {tag} P1 incidents to the on-call SRE within five minutes. "
            f"Billing disputes under fifty dollars may be auto-refunded for {tag}. "
            f"Kubernetes crash loops in {tag} clusters: check OOMKilled and limits. "
            f"Regional failover for {tag} requires two platform-team approvals. ")
    reps = target_words // len(para.split()) + 1
    return f"SYSTEM POLICY {tag} v7\n" + para * reps

QS = ["What is step one for a crash loop? Brief:",
      "May we refund $30? Brief:",
      "Who approves failover? Brief:",
      "When do we escalate a P1? Brief:"]

def measure(port, prompt, n_predict=8):
    body = json.dumps({"prompt": prompt, "n_predict": n_predict, "stream": True,
                       "cache_prompt": True, "temperature": 0}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/completion", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.monotonic(); ttft = None; timings = {}
    with urllib.request.urlopen(req, timeout=600) as r:
        for line in r:
            if not line.startswith(b"data: "): continue
            if ttft is None: ttft = (time.monotonic() - t0) * 1000
            chunk = json.loads(line[6:])
            if chunk.get("stop"): timings = chunk.get("timings", {})
    return round(ttft, 1), timings.get("prompt_n", 0)

def row(exp, policy, label, port, ttft, pn):
    ROWS.append(dict(exp=exp, policy=policy, label=label, port=port, ttft_ms=ttft, prompt_n=pn))
    print(f"  [{exp}] {policy:9s} {label:26s} :{port}  TTFT={ttft:8.1f} ms  prompt_n={pn}")

# ---------------- experiments ----------------
def e1():
    print("\nE1 · prefix cache reuse on ONE worker (cold -> hit -> miss)")
    fresh(np=1)
    prefix = build_prefix("ALPHA")
    t, n = measure(PORTS[0], prefix + "\n\nQuestion: " + QS[0]); row("E1", "single", "cold · full prefill", PORTS[0], t, n)
    for i, q in enumerate(QS[1:3], 1):
        t, n = measure(PORTS[0], prefix + "\n\nQuestion: " + q); row("E1", "single", f"hit {i} · same prefix", PORTS[0], t, n)
    t, n = measure(PORTS[1], prefix + "\n\nQuestion: " + QS[2]); row("E1", "single", "miss · fresh replica", PORTS[1], t, n)

def run_policy(exp, policy, tenants, rounds=3, kill_at=None):
    rr_i = 0; alive = list(PORTS)
    keys = sorted(tenants)
    for rnd in range(rounds):
        if kill_at is not None and rnd == kill_at:
            print(f"  [{exp}] --- killing replica :{PORTS[0]} (the pinned one) ---")
            stop(PORTS[0]); alive = [PORTS[1]]
        for tag in keys:
            if policy == "affinity":
                port = alive[keys.index(tag) % len(alive)]
            else:
                port = alive[rr_i % len(alive)]; rr_i += 1
            prompt = tenants[tag] + f"\n\nQuestion: {QS[rnd % len(QS)]}"
            t, n = measure(port, prompt)
            row(exp, policy, f"r{rnd} · {tag}", port, t, n)

def e2():
    print("\nE2 · routing policy: round-robin vs prefix-affinity (2 replicas, 3 tenants)")
    tenants = {t: build_prefix(t) for t in ("ALPHA", "BRAVO", "CHARLIE")}
    for policy in ("rr", "affinity"):
        fresh(np=2)
        run_policy("E2", policy, tenants, rounds=3)

def e3():
    print("\nE3 · control: UNIQUE prefixes (no sharing) - policy should not matter")
    for policy in ("rr", "affinity"):
        fresh(np=2)
        # every request its own prefix: nothing to reuse, both policies pay full price
        uniq = {f"UNIQ{i}": build_prefix(f"UNIQ{i}") for i in range(3)}
        # one round only: with unique prefixes every request is a cold prefill anyway
        run_policy("E3", policy, uniq, rounds=1)

def e4():
    print("\nE4 · failover: kill the pinned replica under affinity")
    tenants = {"ALPHA": build_prefix("ALPHA")}
    fresh(np=2)
    run_policy("E4", "affinity", tenants, rounds=4, kill_at=2)
    start(PORTS[0], np=2)   # restore for whatever runs next

# ---------------- summary ----------------
def summarize():
    def rows(exp, policy=None, warm=False):
        rs = [r for r in ROWS if r["exp"] == exp and (policy is None or r["policy"] == policy)]
        return rs[3:] if warm and len(rs) > 3 else rs
    s = {}
    e1r = rows("E1")
    if e1r:
        s["E1"] = {"cold_ttft": e1r[0]["ttft_ms"], "hit_ttft": round(sum(r["ttft_ms"] for r in e1r[1:3])/2,1),
                   "miss_ttft": e1r[3]["ttft_ms"], "cold_prompt_n": e1r[0]["prompt_n"], "hit_prompt_n": e1r[1]["prompt_n"]}
    for exp in ("E2", "E3"):
        if rows(exp):
            s[exp] = {}
            for pol in ("rr", "affinity"):
                rs = rows(exp, pol, warm=(exp == "E2"))
                if rs:
                    s[exp][pol] = {"mean_ttft": round(sum(r["ttft_ms"] for r in rs)/len(rs),1),
                                   "hit_rate": round(sum(1 for r in rs if (r["prompt_n"] or 9999) < 100)/len(rs),2),
                                   "tokens_prefilled": sum(r["prompt_n"] or 0 for r in rs)}
    e4r = rows("E4")
    if e4r:
        s["E4"] = {"seq_ttft": [r["ttft_ms"] for r in e4r]}
    return s

if __name__ == "__main__":
    which = sys.argv[1:] or ["e1", "e2", "e3", "e4"]
    t0 = time.time()
    try:
        for w in which: globals()[w]()
    finally:
        stop()
    summ = summarize()
    (HERE/"results.json").write_text(json.dumps({"rows": ROWS, "summary": summ}, indent=2))
    with open(HERE/"results.csv", "w") as f:
        f.write("exp,policy,label,port,ttft_ms,prompt_n\n")
        for r in ROWS: f.write(f'{r["exp"]},{r["policy"]},{r["label"]},{r["port"]},{r["ttft_ms"]},{r["prompt_n"]}\n')
    print("\nSUMMARY:", json.dumps(summ, indent=2))
    print(f"done in {time.time()-t0:.0f}s -> results.json / results.csv")
