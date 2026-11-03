# Groq requirements-extraction adapter

BundleGraph now includes an optional `GroqStructuredExtractionProvider` behind the
existing `StructuredExtractionProvider` protocol. It converts one natural-language
request into the existing `ExtractionPayload` contract; it does not select products,
evaluate compatibility, confirm requirements, approve a plan, or execute payment.

## Configuration

Set these values only in the backend environment or deployment secret manager:

```dotenv
GROQ_API_KEY=server-side-secret
GROQ_MODEL=<model ID selected from Groq's current supported catalog>
```

The model ID is intentionally not hardcoded because provider availability changes.
If either variable is missing, `configured_provider()` raises
`ProviderNotConfigured` and the application remains fail-closed.

## Verified interface

The adapter uses Groq's documented `POST https://api.groq.com/openai/v1/chat/completions`
chat-completions contract with bearer authentication and JSON-object response mode.
The response is parsed locally and then validated by Pydantic using the existing
`ExtractionPayload` model. JSON mode guarantees JSON syntax only; it does not make
the model semantically trustworthy, so schema validation remains mandatory.

References:

- [Groq quickstart](https://console.groq.com/docs/quickstart)
- [Groq API reference](https://console.groq.com/docs/api-reference)
- [Groq structured outputs](https://console.groq.com/docs/structured-outputs)

The repository does not claim a live Groq call has succeeded. Tests inject a
deterministic HTTP response and never require a credential or network access.

## Safety and handoff

- User text is delimited as untrusted data; prompt-injection text cannot grant
  confirmation or payment authority.
- Provider failures return stable adapter errors and do not fabricate a draft.
- Request text and API keys must not be logged.
- Member 2 should inject `configured_provider()` only for draft interpretation.
- Member 3 should render `provider_mode="groq"` separately from fixture mode.
