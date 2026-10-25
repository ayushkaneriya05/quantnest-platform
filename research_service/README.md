# QuantNest research service

This internal FastAPI service runs the AI conversation loop. Django owns users,
admission, evidence, tools, saved answers, confirmations and commercial credits.
The browser calls Django only. Do not expose service port 8001 publicly.

Read [AI Research architecture](../docs/ai-research.md) for the complete flow,
token accounting, tool list, contracts, extension points, verification and migration.

## Files

| File | Responsibility |
|---|---|
| `main.py` | HTTP authentication, streaming, deadline, disconnect cleanup and concurrency |
| `schemas.py` | Request and structured-answer contract; tested against Django's actual payload |
| `workflow.py` | Provider-independent model/tool loop and cumulative reported usage |
| `providers.py` | Adapter interface, Gemini SDK integration, native continuation, retries and usage normalization |

## Configuration

```dotenv
RESEARCH_PROVIDER=gemini
RESEARCH_MODEL=gemini-3.5-flash
GEMINI_THINKING_LEVEL=low
RESEARCH_PROVIDER_TIMEOUT_SECONDS=60
GEMINI_API_KEY=your-provider-key
RESEARCH_SERVICE_TOKEN=your-shared-internal-token
RESEARCH_INTERNAL_API_URL=http://127.0.0.1:8000/api/v1/research/tools/
```

Use a model enabled in your project that supports Interactions, function calling
and structured output together. The model default does not guarantee account
access. Put the same internal service token in Django; never send either secret
to the frontend. Model requests use `store=False`; only the adapter retains native
steps/signatures while the request runs. Application history is provider-independent.

`GEMINI_THINKING_LEVEL=low` reduces generation latency; use `medium` or `high`
when additional reasoning is worth the wait. Choose a level supported by your
model. `RESEARCH_PROVIDER_TIMEOUT_SECONDS` bounds one complete model round,
including connection and retry time. The adapter permits one retry for transient
HTTP errors; SDK retries are disabled so attempts do not multiply. A timeout is
reported directly and does not trigger another potentially billed generation.
The ten-minute research deadline still covers multiple model/tool rounds.
Gemini receives compact schemas describing field types and allowed choices;
Pydantic and Django enforce length, count, ownership and value limits. This
avoids constrained-decoder state explosions from nested bounded tool arguments.

Service logs record slot wait, model-round duration, tool calls and token counts
without recording prompts or credentials. A `200 OK` means the research event
stream opened; the final result/error event determines whether research succeeded.

For native development, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn research_service.main:app --env-file research_service/.env --host 127.0.0.1 --port 8001
```

Run Django and its existing compute Celery worker too. Research shares that worker
with backtests; queue delays are expected while it is busy. Standalone screening
uses deterministic Django tools and needs no AI call. Do not add another queue.

For Compose, use your mode's `research.env`. Compose supplies the internal Django
URL. Development enables the `research` profile; Public/Private include research
in their normal deployment. See [Development](../infra/development/SETUP.md),
[Public](../infra/public/SETUP.md), [Private](../infra/private/SETUP.md) and
[integration setup](../infra/shared/INTEGRATIONS.md#5-gemini-ai-research).

## Upgrading existing deployments

Rename `GEMINI_MODEL` to `RESEARCH_MODEL`, set `RESEARCH_PROVIDER=gemini`, and
remove `RESEARCH_INPUT_TOKEN_BUDGET` / `RESEARCH_OUTPUT_TOKEN_BUDGET` from Django.
Deploy backend and research images together after research has finished. Apply
`commercial.0016_research_token_credits` and rebuild the frontend. The migration
preserves history and starts fresh token accounting; it refuses active research
or subscriptions needing a reviewed terms transition.

One credit is 1,000 reported tokens. Successful saved answers settle actual usage;
failed/cancelled requests charge no customer credits. There is no cumulative
customer token cap per request. The service retains technical provider limits,
a ten-minute deadline supplied by Django, eight uncached tool executions, bounded
retries and bounded model rounds. A valid structured answer returns immediately.

The system instruction separates educational replies, admitted data/evidence,
customer-defined drafts, report reviews and confirmed UI actions. A rejected tool
call is returned to the model as an explicit error. One malformed final answer
may be repaired using validation feedback; that repair cannot fetch new data.
Blank answers and follow-up text beyond the application limits are validated in
the service before saving. Invalid optional proposals do not remove valid ones.

## Verification

```powershell
.\.venv\Scripts\python.exe -m compileall -q research_service
.\.venv\Scripts\python.exe backend/manage.py check
```

Repository test suites are removed; CI retains compilation and configuration checks.
After deployment, submit one real educational question and compare saved
`usage.total_tokens / 1000` with the displayed credits and Billing. `/health`
confirms startup only; it does not verify provider access.

Provider references: [Interactions](https://ai.google.dev/gemini-api/docs/interactions-overview),
[structured output](https://ai.google.dev/gemini-api/docs/structured-output),
[reported usage](https://ai.google.dev/gemini-api/docs/tokens).
