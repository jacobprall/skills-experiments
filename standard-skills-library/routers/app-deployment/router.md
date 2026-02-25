---
type: router
name: app-deployment
domain: app-deployment
routes_to:
  - primitives/streamlit-in-snowflake
  - primitives/spcs-deployment
  - playbooks/build-react-app
---

# App Deployment

Routes application deployment requests to Streamlit in Snowflake (native) or SPCS (containerized).

## Decision Criteria

| Input | How to Determine | Example User Statements |
|-------|-----------------|------------------------|
| **Framework** | Streamlit, React, Next.js, or other? | "Build a Streamlit app", "Deploy my React app" |
| **Complexity** | Data dashboard or full web application? | "Quick dashboard", "Full CRUD app" |
| **Requirements** | Need custom packages, GPU, or external access? | "Uses TensorFlow", "Needs to call external API" |

## Routing Logic

```
Start
  ├─ User wants to BUILD A FULL APP end to end (React/Next.js)?
  │   └─ YES → playbooks/build-react-app
  │
  ├─ App is Streamlit?
  │   ├─ Standard packages, Snowflake data access only?
  │   │   └─ YES → primitives/streamlit-in-snowflake
  │   │
  │   └─ Needs custom packages, external access, or GPU?
  │       └─ YES → primitives/spcs-deployment (containerized Streamlit)
  │
  └─ User has an existing Docker app to deploy?
      └─ YES → primitives/spcs-deployment
```

## Routes To

| Target | Mode | When Selected | What It Provides |
|--------|------|---------------|------------------|
| `playbooks/build-react-app` | Playbook | Broad intent: build a full React/Next.js app from scratch | End-to-end workflow: scaffold → connect to Snowflake → build UI → deploy to SPCS |
| `primitives/streamlit-in-snowflake` | Reference | Narrow: Streamlit app with standard packages and Snowflake data | `snow streamlit deploy`, `snowflake.yml`, `get_active_session()` |
| `primitives/spcs-deployment` | Reference | Narrow: deploy an existing containerized app, or Streamlit needing non-standard packages | Dockerfile, compute pools, service creation, image registry |
| *(multiple primitives)* | Guided | Moderate intent: user has a deployment goal that doesn't fit a pre-built playbook | Agent constructs a plan from relevant primitives, user approves before execution |

## Anti-patterns

| Mis-routing | Why It Happens | Correct Route |
|-------------|----------------|---------------|
| Deploying React to Streamlit in Snowflake | Streamlit in Snowflake only supports Streamlit apps | Use SPCS for React/Next.js |
| Using SPCS for a simple Streamlit dashboard | SPCS adds container management overhead | Use native Streamlit in Snowflake for standard use cases |
