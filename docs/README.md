# QuantNest documentation

**Source review: 16 October 2026.** These guides describe the repository at this
date. Implemented code, a configured provider account and a validated production
deployment are separate things. Remaining delivery work is identified in the
implementation plan and execution limitations.

## Choose a guide

| Your task | Start here | What it owns |
| --- | --- | --- |
| Understand the product and business direction | [Business plan](business-plan.md) | Customers, positioning, subscriptions, Private services and priorities |
| See delivery scope and remaining work | [Implementation plan](implementation-plan.md) | Current implementation map, release gates and future work |
| Plan the future strategy language and builder | [Strategy builder plan](strategy-builder-plan.md) | Research, original-proposal review, compiled rules/state, sizing/routing, all-market extension contracts and phased delivery; implementation deferred |
| Install or upgrade a deployment | [Infrastructure guide](../infra/README.md) | Development, Public and Private setup, exact scripts and environment files |
| Configure an external account | [Third-party setup](third-party-setup.md) | Cloudflare, Oracle, email, payments, authentication, data and research credentials |
| Operate subscriptions, support or Private customers | [Commercial operations](commercial-operations.md) | Customer actions, Admin decisions, routine automation, records and failure recovery |
| Run execution services | [Backend runtime](backend-runtime.md) | Processes, worker sizing, launch, health, safe restart and configuration |
| Trace a tick, order, fill or backtest | [Execution technical reference](execution-technical-reference.md) | Detailed call chains, state, storage, failure boundaries and current limitations |
| Develop strategy configuration | [Strategy configuration](strategy-configuration.md) | Rules, sizing, versions, sharing, deployment and auto-disable configuration |
| Understand reports and journal reviews | [Execution review](execution-review.md) | Source-specific accounting, filters, reviews, exports and research evidence |
| Understand sign-in and security | [Authentication](authentication.md) | Sessions, CSRF, 2FA, Admin, OAuth, avatars and account recovery |
| Maintain the React customer site | [Customer site](customer-site.md) | Routing, catalog ownership, content, illustrations, themes and workspace integration |
| Run the separate AI service | [Research service](../research_service/README.md) | Private service setup, protocol, tools, model configuration and isolation |
| Maintain frontend structure | [Customer site structure](customer-site.md#1-entry-points-and-layouts) | Feature folders, shared components, layouts and route ownership |

Historical input: [original strategy builder proposal](archive/strategy-builder-original-proposal.md).
It is preserved in full as a future-design source. Its old file paths, branch
instructions and proposed behavior do not describe the current implementation.

## Filename convention

Use lowercase topic names with hyphens, for example `backend-runtime.md` or
`strategy-builder-plan.md`. Keep `README.md` as the conventional folder index.
Avoid project-name prefixes, spaces, numbered download suffixes and mixed casing.
Historical proposals belong in `archive/` with their status and successor linked.

For end users, the application provides searchable guides at `/docs/`. Those
articles explain product tasks. This folder explains the underlying system and
operator responsibilities.

## One owner for each subject

- Deployment commands and environment examples belong to `infra/`; follow the
  selected mode's README instead of combining instructions from different modes.
- Customer and operator workflows belong to Commercial operations. The business
  plan explains direction; it is not an alternative operational procedure.
- `backend/commercial/catalog.py` and published database catalog terms own plans.
  Documentation examples do not change allowances or an existing purchase.
- Backend enums and support metadata own API values and customer-facing labels.
  React owns routes and presentation. There is no generated root JSON catalog.
- Execution internals belong to the technical reference; runtime commands belong
  to the runtime guide. Neither establishes a measured latency guarantee.

## Updating these guides

1. Trace the frontend action, API/service, database mutation and background work.
2. Document the implemented behavior, including rejection and recovery cases.
3. Link to the owning guide instead of copying its complete procedure.
4. Mark provider setup, operator decisions and future work explicitly.
5. When changing a path, endpoint, setting or model, update its guide and links.
6. Preserve a valuable future proposal as an explicitly marked plan/archive;
   absence of its implementation alone is not a reason to delete the design.

Historical migrations remain part of installation even when their retired
features are no longer documented as current functionality. Removed benchmark
artifacts and old verification results are not production acceptance evidence.
