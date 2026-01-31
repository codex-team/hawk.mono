# Hawk: Task Manager Integration — Auto Task Creation & Fix with Copilot

> Working title: **Automatic Error Fixing / Task Manager Integration**

---

## 0. Terminology

- **Project** — A project in Hawk.
- **Event** — An error event (or an aggregated error document) stored in `events:<projectId>`.
- **Original Event** — The original error representation (stacktrace, message, etc.).
- **groupHash** — Identifier that groups identical errors. Based on event title.
- **totalCount** — Total number of error repetitions for all time. Original Event property.
- **Task Manager** — External system for tracking tasks (GitHub, Jira, etc.).
- **Task Manager Item** — A universal representation of an external task linked to an Event.

---

## 1. Goal

1. Automatically create a task (GitHub Issue) when an error reaches a repetition threshold (`totalCount`).
2. Store the link between an error and an external task directly in `events:<projectId>`.
3. Allow manual actions:
   - create a task
   - trigger automatic fixing via an agent (Copilot for GitHub)
4. Design the system to be extensible for other task managers (Jira, Linear, etc.).

---

## 2. Flow

1. Workspace admin opend Project Settings → **Task Manager Integration**
2. Connected GitHub Repository
   - See [GitHub Connection Flow](#9-github-connection-flow)
3. Enable Auto Task Creation
4. Specify threshold for auto task creation
5. Enable Assign Agent to new tasks
6. Hawk Worker "TaskManager" is running by schedule and creates tasks for events with totalCount >= threshold
7. Task is created by connected integration (GitHub) **using installation access token** (on behalf of GitHub App)
8. Copilot is assigned to the task **using user-to-server OAuth token** (on behalf of authorized user)
   - Note: Copilot assignment requires user-level permissions and cannot be done with installation tokens alone
9. Copilot fixes the issue and opens a PR.
10. User is needed to review the PR and merge it. 

--

## 3. UI / UX

### 3.1 Project Settings → **Task Manager Integration**

**Connect button**

- Button: **Connect GitHub Repository**
- After connection:
  - `Connected to owner/repo`
  - Actions: **Change**, **Disconnect**

**Auto Task Creation**

- Field: **Create Issue when total repeats ≥ N**
  - integer, min = 1
- Description: *Uses total number of error repetitions for all time (**`totalCount`**).*

**Agent**

- Switch: **Assign agent to new tasks**
- Description: *If the agent is unavailable, the task will be created without an assignee.*

---

### 3.2 Error page (Event details)

**Task Manager block**

Possible states:

1. Task already exists

   - Button-link: **Issue #123**

2. No task exists

   - Button: **Create an Issue**

3. Action button (visible when a task manager is connected)

   - **Fix with Copilot**
     - If no task exists → creates it
     - Then tries to assign the agent (best-effort)

---

## 4. Data Storage

### 4.1 Project document (`projects`)

Task manager configuration is stored directly in the project document using a universal structure.

```ts
projects[<projectId>].taskManager = {
  type: 'github',                 // future: 'jira', 'linear', ...

  autoTaskEnabled: boolean,       // enables scheduled auto task creation
  taskThresholdTotalCount: number,

  assignAgent: boolean,           // if true: assign an agent to newly created tasks (for GitHub: Copilot)

  // runtime usage tracking for daily auto-task budget (Variant B)
  usage: {
    dayStartUtc: Date,            // UTC day boundary (e.g. 2026-01-17T00:00:00.000Z)
    autoTasksCreated: number      // how many auto-created tasks were created since dayStartUtc
  },

  connectedAt: Date,
  updatedAt: Date,

  config: {
    // typed by `type`

    // github:
    installationId: string,
    repoId: string | number,
    repoFullName: string
  }
}
```
---

### 4.2 Events collection (`events:<projectId>`)

Each Event may reference **one** external task via a universal structure.

```ts
events:<projectId>
{
  _id: ObjectId,
  groupHash: string,
  totalCount: number,

  taskManagerItem?: {
    type: 'github-issue',

    number: number,
    url: string,
    title: string,

    createdBy: 'auto' | 'manual',
    createdAt: Date,

    assignee: 'copilot' | null
  }
}
```

**Rules:**

- If `taskManagerItem` exists → a task already exists and must not be created again automatically.
- `assignee` is intentionally generic and task-manager-agnostic.

---

## 5. Automatic Task Creation

### 5.1 Scheduled worker

Auto task creation is handled by a **scheduled worker**, not during event ingestion.
Cron Manager is responsible for running the worker by schedule. See [Cron Manager](../cron-manager/README.md) for more details.

**Schedule example:**

- Runs once every **N minutes** (e.g. once per hour).

### 5.2 Rate limiting

To protect repositories from spam, Hawk enforces a hard limit:

- **No more than ****MAX\_AUTO\_TASKS\_PER\_DAY**** auto-created tasks per repository per day**

Suggested behavior:

- Manual actions (*Create an Issue*, *Fix with Copilot*) are **not** rate-limited in MVP (product decision).
- Only scheduled auto-creation is rate-limited.

> Day boundary: recommended to use **UTC** for consistency.

### 5.3 Worker algorithm

1. Select projects where:

   - `projects.taskManager` exists
   - `projects.taskManager.type === 'github'`
   - `projects.taskManager.autoTaskEnabled === true`

2. For each project:

   - read `connectedAt`
   - compute today’s UTC start (`dayStartUtc`)

3. Check daily budget for rate limiting:

- Use `projects.taskManager.usage` as the source of truth.

Algorithm per project (UTC day boundary):

1. Compute `dayStartUtc` for “today”.
2. If `usage.dayStartUtc` is missing or differs from `dayStartUtc`:
   - reset `usage = { dayStartUtc, autoTasksCreated: 0 }`.
3. If `usage.autoTasksCreated >= MAX_AUTO_TASKS_PER_DAY`:
   - skip auto-creation for this project until the next day.
4. When the worker decides to create an auto task, it must **atomically increment** `usage.autoTasksCreated` (with a guard that it is still `< MAX_AUTO_TASKS_PER_DAY`).
   - If the atomic increment fails (budget already exhausted by another worker run), skip creation.

4) If budget is available, scan `events:<projectId>` where:

   - `taskManagerItem` does **not** exist
   - event `timestamp` >= `connectedAt`
   - `totalCount >= taskThresholdTotalCount`

5) For each matching Event (until budget is exhausted):

   - create a GitHub Issue
   - write `taskManagerItem` into the Event document with `createdBy: 'auto'`

> Result: each qualifying error produces **exactly one** external task, even across multiple worker runs.

---

## 6. Manual Actions

### 6.1 Create an Issue (Event mutation)

Triggered from the Event page.

Rules:

- If `taskManagerItem` already exists → action is disabled.
- Otherwise:
  - create GitHub Issue
  - store `taskManagerItem.createdBy = 'manual'`

---

### 6.2 Fix with Copilot (Event mutation)

Triggered from the Event page.

Logic:

1. If `taskManagerItem` does not exist:

   - create Issue (manual)

2. If `projects.taskManager.assignAgent === true`:

   - attempt to assign Copilot
   - update:
     - `taskManagerItem.assignee = 'copilot'` (if successful)

3. If Copilot is unavailable:

   - Issue remains unassigned
   - no hard error, best-effort behavior

---

### 6.3 Disconnect Task Manager (Project mutation)

Triggered from Project Settings → **Task Manager Integration** page.

**Rules:**

- User must be workspace admin (enforced by `@requireAdmin` directive)
- If `taskManager` does not exist → action is disabled
- Otherwise:
  - Remove `taskManager` configuration from Project document
  - Update `updatedAt` timestamp
  - Return updated Project

**Behavior:**

- This action is irreversible (user must reconnect to restore integration)
- All auto task creation for this project stops immediately
- Existing `taskManagerItem` references in Events remain intact (historical data)

---

### 6.4 Update Task Manager Settings (Project mutation)

Triggered from Project Settings → **Task Manager Integration** page.

**Rules:**

- User must be workspace admin (enforced by `@requireAdmin` directive)
- Project must have `taskManager` configuration
- Input validation:
  - `autoTaskEnabled`: boolean
  - `taskThresholdTotalCount`: integer, min = 1
  - `assignAgent`: boolean

**Logic:**

1. Update `projects.taskManager.autoTaskEnabled`
2. Update `projects.taskManager.taskThresholdTotalCount`
3. Update `projects.taskManager.assignAgent`
4. Update `projects.taskManager.updatedAt`
5. Return updated Project

**Notes:**

- If `autoTaskEnabled` is set to `false`, scheduled worker will skip this project
- If `taskThresholdTotalCount` is changed, next worker run will use the new threshold
- `assignAgent` only affects newly created tasks (existing issues are not modified)

---

## 7. GitHub API Integration Details

### 7.1 Authentication Strategy

Hawk uses **two different authentication methods** for different operations:

1. **Installation Access Tokens** (GitHub App) — for creating issues
2. **User-to-Server OAuth Tokens** (User authorization) — for assigning Copilot

#### 7.1.1 Installation Access Token

GitHub App uses **installation access tokens** to authenticate API requests on behalf of an installed application.

**Token Lifecycle:**

- Installation access tokens are obtained by calling GitHub API: `POST /app/installations/{installation_id}/access_tokens`
- Each token is valid for **1 hour** from the time it's issued
- Tokens are **scoped** to the installation and repository permissions configured in the GitHub App
- Hawk must request a new token when the current one expires

**Token Usage:**

The `createInstallationToken(installationId)` method is called **internally** by `GitHubService` methods before making GitHub API requests:

1. **Before creating an Issue** (`createIssue` method):
   - Calls `createInstallationToken(installationId)` to get a valid token
   - Uses the token to authenticate `POST /repos/{owner}/{repo}/issues` request
   - Issues are created **on behalf of the GitHub App** (not the user)

**Implementation Notes:**

- GitHubService can implement token caching (store token + expiration time) to avoid unnecessary API calls
- If token is expired or missing, request a new one automatically
- Token creation requires:
  - GitHub App ID (`GITHUB_APP_ID`)
  - GitHub App Private Key (`GITHUB_PRIVATE_KEY`)
  - Installation ID (stored in `project.taskManager.config.installationId`)

**Token Request Flow:**

1. Create JWT token signed with private key (valid for 10 minutes)
2. Use JWT to authenticate request to `POST /app/installations/{installation_id}/access_tokens`
3. GitHub returns installation access token (valid for 1 hour)
4. Use installation access token for repository API calls

#### 7.1.2 User-to-Server OAuth Token

**User-to-server OAuth tokens** are required for assigning Copilot to issues, as Copilot assignment requires user-level permissions.

**Why User Tokens for Copilot Assignment:**

- GitHub Copilot agent assignment requires **user-level permissions** and cannot be performed using installation tokens alone
- The assignment must be done **on behalf of the user** who authorized the GitHub App

**Token Lifecycle:**

- User tokens are obtained through OAuth flow during GitHub App installation
- Tokens have expiration dates and can be refreshed using refresh tokens
- Tokens are stored in `project.taskManager.config.delegatedUser.accessToken`
- Tokens are automatically refreshed when they expire or become invalid (401 response)

**Token Usage:**

1. **Before assigning Copilot** (`assignCopilot` method):
   - Uses `delegatedUser.accessToken` from project configuration
   - Uses the token to authenticate GraphQL mutation `addAssigneesToAssignable`
   - Copilot assignment is performed **on behalf of the authorized user**

**Token Refresh Flow:**

1. When a 401 error is received during Copilot assignment, the system attempts to refresh the token
2. Uses `refreshToken` from `delegatedUser.refreshToken` to obtain a new access token
3. Updates `delegatedUser.accessToken` and `delegatedUser.refreshToken` in the project configuration
4. Retries the original operation with the new token

**OAuth Flow:**

1. User installs GitHub App with "Request user authorization (OAuth) during installation" enabled
2. GitHub redirects to `callbackUrl` with authorization code
3. Hawk exchanges the code for access token and refresh token
4. Tokens are stored in `project.taskManager.config.delegatedUser`

---

## 8. GitHub Issue Format (MVP)

**Title**

```
[Hawk] <error title>
```

**Body**

- Link to Hawk Event page
- totalCount
- firstSeen / lastSeen (if available)
- Stacktrace / top frames (trimmed)
- Technical marker:
  ```
  hawk_groupHash: <groupHash>
  ```

**Labels**

- `hawk:error`

---

## 9. API / Schema Changes (High-level)

### Project-level

- Add `taskManager` configuration to Project
- HTTP endpoints:
  - `GET /integration/github/connect?projectId=<projectId>` — initiate GitHub connection
  - `GET /integration/github/callback?state=<state>&installation_id=<installation_id>` — handle GitHub App installation callback
- Mutations (Project):
  - disconnectTaskManager
  - updateTaskManagerSettings

### Event-level

- Extend Event with `taskManagerItem`
- Mutations (Event):
  - createTaskForEvent
  - fixEventWithCopilot

---

## 10. GitHub Connection Flow

0. We need to create a GitHub App with the following settings:
   - **Permissions:**
     - Issues: Read, Write
     - Actions: Read, Write
     - Content: Read, Write
     - Pull Requests: Read, Write
     - Metadata: Read-only
   - **User authorization callback URL:** `https://api.hawk.so/integration/github/oauth`
     - This URL is used for OAuth flow to obtain user-to-server tokens
   - **Setup URL:** Leave empty (not used)
   - **Request user authorization (OAuth) during installation:** ✅ **Enable this option**
     - This is required to obtain user-to-server OAuth tokens for Copilot assignment
     - Without this, only installation tokens will be available, which cannot assign Copilot
    
1. Workspace admin clicks **Connect GitHub Repository** button in Garage
2. Garage makes fetch request to Hawk API endpoint `/integration/github/connect?projectId=<projectId>` with Authorization header
3. Hawk API generates GitHub App installation URL with state parameter (CSRF protection)
   - URL format: `https://github.com/apps/<app-name>/installations/new?state=<state>`
   - State is stored in Redis with TTL 15 minutes for CSRF protection
4. Hawk API returns JSON response with `redirectUrl` field
5. Garage redirects user to GitHub installation page using `window.location.href = redirectUrl`
6. User is asked to install GitHub App and select repositories (GitHub allows selecting multiple repositories during installation)
7. GitHub redirects to Hawk API callback endpoint `/integration/github/callback?state=<state>&installation_id=<installation_id>`
8. Hawk API validates state parameter (retrieves from Redis and consumes it atomically)
9. Hawk API uses `installation_id` from callback parameters to save configuration
10. Hawk API saves the project taskManager configuration with installation ID (repoId and repoFullName are empty initially)
11. Hawk API redirects to Garage with success message: `/project/<projectId>/settings/task-manager?success=true`
12. Garage detects `success=true` parameter, then makes request to Hawk API endpoint `/integration/github/repositories?projectId=<projectId>` to get list of accessible repositories
13. Hawk API retrieves `installationId` from project's `taskManager.config.installationId` stored in database
14. Hawk API queries GitHub API for repositories accessible to the installation using installation access token
15. Hawk API returns list of repositories (ephemeral data, not stored in database) to Garage
16. Garage displays RepoPicker modal with list of repositories for user to select
17. User selects a repository from the list
18. Garage sends selected repository info to Hawk API (via GraphQL mutation `updateTaskManagerSettings` or new endpoint) to update `repoId` and `repoFullName` in project configuration
19. GitHub integration is fully configured and ready to use

---

## 11. GitHub Webhooks

GitHub App sends webhook events to Hawk API for tracking installation changes.

### 10.1 Webhook Endpoint

**Endpoint:** `POST /integration/github/webhook`

**Authentication:** 
- GitHub signs webhook payloads using HMAC SHA-256
- Signature is provided in `X-Hub-Signature-256` header
- Webhook secret must match `GITHUB_WEBHOOK_SECRET` environment variable

### 10.2 Supported Events

#### 10.2.1 `installation.deleted`

Triggered when GitHub App installation is deleted from a repository or organization.

**Handler Logic:**

1. Receive webhook payload with `action: 'deleted'` and `installation.id`
2. Find all projects where `taskManager.config.installationId` matches the deleted installation ID
3. Remove `taskManager` configuration from these projects
4. Log the removal for audit purposes

**Result:** 
- Projects lose their GitHub integration configuration
- Auto task creation stops for these projects
- Existing `taskManagerItem` references in Events remain intact (historical data)

**Other Events:**

- `installation.created`, `installation.suspend`, etc. are logged for monitoring but don't trigger automatic actions in MVP

---

## 12. Non-Goals (for this iteration)

- PR tracking / merge detection
- Auto-closing tasks
- Multiple task manager implementations (only GitHub supported, schema-ready for others)

---

## 13. Acceptance Criteria

- Task Manager integration configured per Project
- Scheduled worker creates GitHub Issues based on `totalCount`
- Each Event can have **only one** Task Manager Item
- Manual and automatic flows share the same storage model
- Event page shows clear actions and links
- Architecture is extensible for Jira / other systems

---



