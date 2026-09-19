#!/usr/bin/env python3
"""REC 2/3 · 3 tenants interleaved. Usage: python3 tenants.py <ENDPOINT_IP> [model] [rounds]
Point it at the blind Service IP (REC 2) then the EPP IP (REC 3). TTFT is wall-clock
to the first streamed token. Pod attribution: keep `kubectl logs -f` of the pods
(or the EPP) in the second tmux pane while this runs."""
import json, sys, time, urllib.request
IP=sys.argv[1]; MODEL=sys.argv[2] if len(sys.argv)>2 else "meta-llama/Llama-3.2-3B-Instruct"
ROUNDS=int(sys.argv[3]) if len(sys.argv)>3 else 3
def prefix(tag):
    p=(f"You are the dedicated copilot for tenant {tag}. Follow the {tag} runbook. "
       f"Escalate {tag} P1 incidents within five minutes. Check OOMKilled and limits. ")
    return f"SYSTEM POLICY {tag} v7\n"+p*60
QS=["First step for a crash loop?","May we refund $30?","Who approves failover?"]
def ask(prompt):
    body=json.dumps({"model":MODEL,"prompt":prompt,"max_tokens":8,"stream":True}).encode()
    req=urllib.request.Request(f"http://{IP}/v1/completions",data=body,
                               headers={"Content-Type":"application/json"})
    t0=time.monotonic(); ttft=None
    with urllib.request.urlopen(req,timeout=1200) as r:
        for line in r:
            if line.startswith(b"data:") and ttft is None:
                ttft=(time.monotonic()-t0)*1000; break
    return ttft
ttfts=[]
for rnd in range(ROUNDS):
    for tag in ("ALPHA","BRAVO","CHARLIE"):
        t=ask(prefix(tag)+f"\nQ: {QS[rnd%3]}")
        ttfts.append(t); print(f"r{rnd} {tag:7s} TTFT={t:9.1f} ms")
warm=ttfts[3:] or ttfts
print(f"\nwarm-mean TTFT: {sum(warm)/len(warm):.0f} ms ({len(warm)} requests)")
