# Investigation evaluation cases

## RUN-1042 — Cap below passing requirement

Facts:
- Measured throughput: 42 Mbps.
- Required minimum: 100 Mbps.
- Saved rate limit: 50 Mbps.

Expected findings:
- Measured throughput failed the requirement.
- The saved cap is below the required minimum.
- If enforced, the cap prevents passing.
- Saved configuration does not prove runtime enforcement.
- The exact reason for measuring 42 Mbps remains unknown.

Incorrect claims:
- The cap was definitely enforced.
- Congestion or packet loss was confirmed.
- The cap explains the exact measured value of 42 Mbps.

## RUN-1043 — Cap above passing requirement

Facts:
- Measured throughput: 42 Mbps.
- Required minimum: 100 Mbps.
- Saved rate limit: 200 Mbps.

Expected findings:
- Measured throughput failed the requirement.
- There is no cap-versus-threshold conflict.
- A 200 Mbps limit does not guarantee achieving 100 Mbps.
- The cause of the low throughput remains unknown.

Incorrect claims:
- 200 Mbps is below 100 Mbps.
- Applying the cap guarantees passing.
- Congestion or packet loss was confirmed.