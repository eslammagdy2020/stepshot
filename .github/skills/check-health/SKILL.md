---
name: check-health
description: Pings the company website and returns
             HTTP status + response time
type: shell
command: |
  curl -o /dev/null -s -w \
  "Status: %{http_code}\nTime: %{time_total}s\n" \
  https://linkagency.com
timeout: 10s