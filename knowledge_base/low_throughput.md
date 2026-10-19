# Throughput below the expected threshold

Document ID: KB-003

## When this guide applies

The log contains THROUGHPUT_BELOW_THRESHOLD.
Traffic started, throughput was measured, and the measured result
was below the configured minimum.

## Meaning

This is a performance failure after successful test setup.
It is not the same as a test that aborted before traffic started.

## Possible causes

- Network congestion.
- Device resource limits.
- Traffic configuration mismatch.
- Packet loss.

## Recommended checks

- Compare measured throughput with the configured threshold.
- Inspect traffic configuration and measurement duration.
- Inspect packet loss and device resource usage.
- Compare against a successful run under similar conditions.

Do not change the threshold simply to make the test pass.
Low throughput alone does not establish the root cause.