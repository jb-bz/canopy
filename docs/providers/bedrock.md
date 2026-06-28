# AWS Bedrock

canopy ships with **BedrockProvider** which calls **AWS Bedrock InvokeModel** using **AWS Signature V4** for authentication — implemented inline using stdlib `hmac`/`hashlib` (no `boto3` dependency).

## When to use this provider

- You're running on AWS and want to use Bedrock-managed models
- You need access to AWS-only models (Titan, certain Llama variants, etc.)
- You have an AWS account with Bedrock model access enabled and want to bill through your AWS account

## Models supported by canopy's implementation

canopy's `BedrockProvider` uses the **Anthropic Messages body shape**, so it works with any Bedrock model that accepts that shape:

- `anthropic.claude-3-5-sonnet-20241022-v2:0`
- `anthropic.claude-3-sonnet-20240229-v1:0`
- `anthropic.claude-3-haiku-20240307-v1:0`

For models with a different body shape (Titan, Llama, Mistral), use a **BYO provider** — see [BYO.md](BYO.md).

## Default model

`anthropic.claude-3-sonnet-20240229-v1:0`

## Endpoint

```
POST https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke
```

## Auth: AWS SigV4 (implemented in canopy)

Bedrock uses AWS Signature V4. canopy signs requests inline:

| Step | What |
|---|---|
| 1 | Build canonical request (method, path, headers, payload hash) |
| 2 | Build string-to-sign with credential scope `date/region/service/aws4_request` |
| 3 | Derive signing key: `k_date → k_region → k_service → k_signing` via HMAC-SHA256 |
| 4 | Sign string-to-sign with `k_signing` |
| 5 | Build `Authorization: AWS4-HMAC-SHA256 Credential=..., SignedHeaders=..., Signature=...` |

The signing code lives in `canopy/providers.py:bedrock_sigv4_sign()` and is unit-tested in `tests/test_phase4_providers.py`.

## Required credentials

| Credential | Source |
|---|---|
| AWS access key ID | IAM console → Users → Security credentials |
| AWS secret access key | Same as above |
| AWS region | Where you enabled Bedrock (e.g. `us-east-1`, `eu-west-1`) |

You can also use an IAM role's temporary credentials (via STS) — same flow, just pass the temp keys.

## Setup

```sh
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_REGION="us-east-1"

canopy setup --non-interactive \
    --provider bedrock \
    --model anthropic.claude-3-sonnet-20240229-v1:0 \
    --api-key "$AWS_ACCESS_KEY_ID" \
    --client claude-code --global-config
```

For `--api-key`, pass the **access key ID**. The secret access key is read from `AWS_SECRET_ACCESS_KEY` (or `--secret-key` flag if you add it; not yet implemented in v0.4.0).

## Why no boto3?

Three reasons:

1. **Footprint.** boto3 is ~30 MB. canopy is ~150 KB.
2. **No transitive deps.** SigV4 is ~30 lines of stdlib. boto3 pulls in `botocore`, `jmespath`, `s3transfer`, etc.
3. **Transparency.** Inline signing means the request shape is in canopy's source, not buried in boto3. Easier to debug, audit, and verify.

If you need features beyond InvokeModel (Converse API, streaming, async), use boto3 directly. canopy's BedrockProvider covers the 80% case of "send a prompt, get text back".

## Limitations

- Only the Anthropic Messages body shape. Llama, Titan, Mistral on Bedrock need BYO.
- No streaming. Single request → single response.
- No tool use. Bedrock-specific tool-use shapes differ from Anthropic's; not implemented.