#!/usr/bin/env python3
"""REC 1 · cold vs hit on the real engine. Runs ON the box.
Usage: python3 hit.py <endpoint_ip:port> <model>"""
import json, sys, time, urllib.request
EP=sys.argv[1]; MODEL=sys.argv[2]
para=("You are the support copilot for AcmeCloud. Follow the runbook strictly. "
      "Escalate P1 incidents to the on-call SRE within five minutes. Kubernetes pod "
      "crash loops should first be checked for OOMKilled status and resource limits. ")
PREFIX="SYSTEM POLICY v7\n"+para*60
def ask(q):
    body=json.dumps({"model":MODEL,"prompt":PREFIX+q,"max_tokens":8,"stream":True}).encode()
    req=urllib.request.Request(f"http://{EP}/v1/completions",data=body,
                               headers={"Content-Type":"application/json"})
    t0=time.monotonic(); ttft=None
    with urllib.request.urlopen(req,timeout=1800) as r:
        for line in r:
            if line.startswith(b"data:") and ttft is None:
                ttft=(time.monotonic()-t0)*1000; break
    return ttft
print("shared prefix: ~3,000 tokens\n")
t=ask("\nQ: first step for a crash loop? Brief:")
print(f"request 1 · COLD · full prefill     TTFT = {t:10.1f} ms")
t=ask("\nQ: when do we escalate a P1? Brief:")
print(f"request 2 · same prefix · HIT       TTFT = {t:10.1f} ms   <- prefill skipped")
