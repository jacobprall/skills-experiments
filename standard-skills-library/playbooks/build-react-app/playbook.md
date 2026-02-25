---
type: playbook
name: build-react-app
domain: app-deployment
depends_on:
  - spcs-deployment
---

# Build a React App with Snowflake Data

Build a Next.js application connected to Snowflake data, deployable to SPCS.

## Objective

A working Next.js application that:
- Queries Snowflake data via API routes using the Snowflake SDK
- Uses a modern UI framework (shadcn/ui + Tailwind)
- Runs locally for development
- Is ready for SPCS deployment

## Prerequisites

- Node.js v20+ and Docker
- Snowflake connection credentials (account, user, password or key)
- Target tables identified

## Pre-execution Probes

Before starting, the agent should probe the environment:

```sql
-- Verify data sources exist and are queryable
SELECT table_catalog, table_schema, table_name, row_count
  FROM <database>.INFORMATION_SCHEMA.TABLES
  WHERE table_name IN (<data_sources>);

-- Check available roles and connection info
SELECT CURRENT_ACCOUNT(), CURRENT_ROLE(), CURRENT_WAREHOUSE();

-- If deploying to SPCS: check compute pool availability
SHOW COMPUTE POOLS;
SHOW IMAGE REPOSITORIES;
```

These probes confirm the data sources exist, verify the user's Snowflake connection context, and check SPCS readiness for deployment.

## Steps

### Step 1: Gather requirements

Clarify with the user:
- What data should the app display? (tables, views, queries)
- What type of app? (dashboard, admin panel, data explorer)
- Any aesthetic direction? (minimal, enterprise, playful)

**Checkpoint:**
  severity: review
  present: "Summary of requirements — data sources, app type, UI direction"

Options: approve, modify (refine scope), abort, different-approach.

### Step 2: Scaffold the project

```bash
npx create-next-app@latest <app-name> --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*"
cd <app-name>
npx shadcn@latest init -d
npx shadcn@latest add card chart button table select input tabs badge skeleton
npm install recharts lucide-react snowflake-sdk
```

Configure `next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  serverExternalPackages: ["snowflake-sdk"],
};

export default nextConfig;
```

Expected errors:

| Pattern | Recovery | Retryable |
|---------|----------|-----------|
| `npm ERR! code ENOENT` | Node.js not installed or not on PATH | No — escalate |
| `npx: command not found` | Node.js version too old | No — escalate |
| `EACCES permission denied` | File system permissions issue | No — escalate |

### Step 3: Set up Snowflake connection

Create `lib/snowflake.ts` with a dual-mode connection pattern:

```typescript
import snowflake from "snowflake-sdk";

function getConnection() {
  // SPCS: uses OAuth token from environment
  if (process.env.SNOWFLAKE_ACCOUNT && process.env.SNOWFLAKE_HOST) {
    return snowflake.createConnection({
      account: process.env.SNOWFLAKE_ACCOUNT,
      host: process.env.SNOWFLAKE_HOST,
      authenticator: "OAUTH",
      token: process.env.SNOWFLAKE_TOKEN,
      warehouse: process.env.SNOWFLAKE_WAREHOUSE,
      database: process.env.SNOWFLAKE_DATABASE,
    });
  }
  // Local dev: uses .env.local credentials
  return snowflake.createConnection({
    account: process.env.SNOWFLAKE_ACCOUNT!,
    username: process.env.SNOWFLAKE_USER!,
    password: process.env.SNOWFLAKE_PASSWORD!,
    warehouse: process.env.SNOWFLAKE_WAREHOUSE,
    database: process.env.SNOWFLAKE_DATABASE,
  });
}

export async function query<T>(sql: string): Promise<T[]> {
  const conn = getConnection();
  return new Promise((resolve, reject) => {
    conn.connect((err) => {
      if (err) return reject(err);
      conn.execute({
        sqlText: sql,
        complete: (err, _stmt, rows) => {
          conn.destroy(() => {});
          if (err) return reject(err);
          resolve((rows || []) as T[]);
        },
      });
    });
  });
}
```

### Step 4: Build API routes and UI

Create API routes in `app/api/` that use the Snowflake connection, and pages that fetch from those routes. Use shadcn/ui components and Recharts for visualization.

**Checkpoint:**
  severity: review
  present: "Test results — pages load, data renders, no console errors"

Verify the app works locally with `npm run dev`. Options: approve (proceed to deployment), modify (fix issues), abort, different-approach.

### Step 5: Deploy to SPCS

Reference: `primitives/spcs-deployment`

Follow the SPCS deployment primitive for:
- Creating a Dockerfile
- Pushing to Snowflake image registry
- Creating the service with a spec that exposes port 8080

Expected errors:

| Pattern | Recovery | Retryable |
|---------|----------|-----------|
| `Docker daemon is not running` | Start Docker Desktop | Yes |
| `unauthorized: authentication required` | Log in to Snowflake image registry | Yes |
| `Compute pool ... does not exist` | Create a compute pool first | No — escalate |

**Compensation:**
```sql
DROP SERVICE IF EXISTS {service_name};
-- Image in repository can be left (no side effects) or manually removed
```

**Creates:**
- type: spcs_service
  name: "{service_name}"

**Checkpoint:**
  severity: critical
  present: "Deployment status — service URL, health check results"

This checkpoint is `critical` because it confirms the application is live. Options: approve (done), modify (adjust config), abort, different-approach.

## Anti-patterns

| Mistake | Impact | Instead |
|---------|--------|---------|
| Using mock/hardcoded data | App doesn't reflect real data | Always connect to real Snowflake tables |
| Exposing credentials in client-side code | Security risk | Use server-side API routes; credentials stay in `.env.local` or SPCS environment |
| Skipping the `standalone` output mode | Docker build fails or image is too large | Set `output: "standalone"` in `next.config.ts` |
| Skipping environment probes | Deploy fails because compute pool or image repo doesn't exist | Always probe SPCS readiness before deployment step |
