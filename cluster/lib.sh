#!/bin/bash
# shared helpers · state lives in cluster/.state
export AWS_PROFILE=cloudfluently AWS_DEFAULT_REGION=us-west-2
STATE="$(dirname "$0")/.state"
KEY=~/.ssh/llmd-demo.pem
save(){ grep -v "^$1=" "$STATE" 2>/dev/null > "$STATE.tmp"; echo "$1=$2" >> "$STATE.tmp"; mv "$STATE.tmp" "$STATE"; }
load(){ [ -f "$STATE" ] && source "$STATE"; }
rssh(){ ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -i "$KEY" ubuntu@"$IP" "$@"; }
rscp(){ scp -o StrictHostKeyChecking=no -i "$KEY" "$@"; }
need_ip(){ load; [ -n "$IP" ] || { echo "no box yet - run ./0_launch_box.sh"; exit 1; }; }
