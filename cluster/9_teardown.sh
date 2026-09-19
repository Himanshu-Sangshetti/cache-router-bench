#!/bin/bash
set -e; cd "$(dirname "$0")"; source ./lib.sh; load
[ -n "$INSTANCE_ID" ] && aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" >/dev/null && echo "terminating $INSTANCE_ID"
rm -f .state
echo "done. (security group llmd-demo left in place - free)"
