# Device connection timeout before traffic starts

Document ID: KB-001
Document type: Troubleshooting guide
Scope: Fictional test automation system

## When this guide applies

Use this guide when:
- The log contains DEVICE_CONNECT_TIMEOUT.
- The failure occurs while connecting to the device control endpoint.
- Traffic generation has not started.

## What the error means

The test runner did not establish a connection to the configured
device address and port within the connection timeout.

This is a setup-stage failure. It does not demonstrate poor throughput.

## Possible causes

1. The configured device IP address or port is incorrect.
2. The device is powered off or unreachable from the test runner.
3. A firewall or network route prevents the connection.
4. The device control service is unavailable or unresponsive.
5. The service is overloaded and cannot respond within the timeout.

A timeout alone does not identify which cause occurred.

## Investigation steps

1. Compare the configured endpoint with the approved device inventory.
2. Check connectivity from the same machine that executed the test.
3. Check whether the device control service is running and listening
   on the expected address and port.
4. Inspect network and firewall evidence for dropped connections.
5. Inspect device service logs around the failure timestamp.

## How to interpret additional evidence

- An endpoint mismatch supports a configuration problem.
- A stopped service supports service unavailability.
- A firewall log showing dropped traffic supports a network block.
- A successful connection now does not prove connectivity was working
  at the time of the failed run.

## Reporting guidance

Report the connection timeout as the observed failure.

List possible causes as hypotheses until additional evidence supports
a root cause.

If traffic never started, report throughput as unavailable, not zero.

Do not recommend changing throughput thresholds to resolve this error.