# Device authentication failure

Document ID: KB-002

## When this guide applies

The log contains AUTHENTICATION_FAILED or INVALID_CREDENTIALS.
The runner connected to the device, but authentication was rejected.

## Meaning

The device responded, but the supplied credentials were not accepted.
This differs from a connection timeout, where a connection was not
established within the allowed time.

## Possible causes

- Incorrect username or password.
- Expired access token.
- Locked or disabled account.

## Recommended checks

- Verify the configured username and credential reference.
- Check token expiry and account status.
- Inspect authentication logs.

Do not print passwords or tokens in the investigation report.
A rejection alone does not establish which credential issue occurred.