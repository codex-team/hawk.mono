# Hawk Architecture

Hawk is an error tracking service built as a microservices-based monorepo. This document describes the overall architecture, components, and data flow of the system.

## Overview

Hawk is designed to collect, process, store, and visualize application errors from various sources. The system follows a microservices architecture with clear separation of concerns, using message queues for asynchronous processing and GraphQL for API communication.

## System Components

### Core Services

#### 1. Collector (`collector/`)

**Technology:** Go  
**Purpose:** Entry point for all error events from client applications

The Collector service is responsible for:
- Receiving error events via HTTP POST, WebSocket, or Sentry-compatible endpoints
- Validating JWT tokens to authenticate requests
- Applying rate limiting per project using Redis
- IP-based blacklisting for DDoS protection
- Routing validated events to appropriate RabbitMQ queues based on catcher type
- Handling Releases (source maps + commits) uploads

**Key Features:**
- Fast HTTP server using `fasthttp`
- Rate limiting with configurable limits at project, workspace, and plan levels
- Redis-based caching for project settings and disabled projects
- Support for multiple transport protocols (HTTP, WebSocket, Sentry envelope)

**Endpoints:**
- `POST /` - Main error collection endpoint
- `WS /ws` - WebSocket endpoint for real-time error streaming
- `POST /release` - Source map upload endpoint
- `POST /api/0/envelope/` - Sentry-compatible endpoint

#### 2. Registry (`registry/`)

**Technology:** RabbitMQ  
**Purpose:** Message broker for asynchronous task processing

The Registry uses RabbitMQ to route messages between services:

**Exchanges:**
- `errors` - Main exchange for error events, routes to language-specific queues
- `stash` - Dead-letter exchange for invalid or failed messages
- `release` - Exchange for source map releases

**Queues:**
- `errors/<language_name>` - Language-specific error queues (e.g., `errors/javascript`, `errors/nodejs`)
- `errors/default` - Default queue for errors without specific handlers
- `errors/sentry` - Queue for Sentry-compatible events
- `stash/<language_name>` - Dead-letter queues for failed messages
- `log` - Queue for logging and notification tasks

**Message Flow:**
1. Collector publishes validated events to the `errors` exchange
2. Exchange routes messages to appropriate queues based on routing keys
3. Workers consume messages from their designated queues
4. Failed messages are routed to `stash` exchange for manual review

#### 3. Workers (`workers/`)

**Technology:** Node.js/TypeScript  
**Purpose:** Background task processors for various error handling operations

Workers are specialized services that consume messages from RabbitMQ queues and perform specific processing tasks. Each worker inherits from a base `Worker` class and implements a `handle` method.

**Worker Types:**

- **Default Worker** (`workers/default/`)
  - Handles standard error events in correct format
  - Processes events with type `errors/*` except those requiring special processing

- **JavaScript Worker** (`workers/javascript/`)
  - Processes JavaScript/TypeScript errors
  - Applies source map transformations to unminify stack traces
  - Handles browser-specific error formatting

- **Grouper Worker** (`workers/grouper/`)
  - Groups similar errors together to reduce noise
  - Identifies error repetitions and patterns
  - Updates event groups in the database
  - Saves events to MongoDB

- **Sender Worker** (`workers/sender/`)
  - Base class for notification workers
  - Handles various notification tasks (event notifications, workspace invites, payment confirmations, etc.)

- **Email Worker** (`workers/email/`)
  - Sends email notifications using SMTP
  - Uses Twig templates for email formatting
  - Handles various email types (event alerts, digests, system notifications)

- **Telegram Worker** (`workers/telegram/`)
  - Sends notifications to Telegram channels
  - Formats messages for Telegram API

- **Slack Worker** (`workers/slack/`)
  - Integrates with Slack webhooks
  - Formats error notifications for Slack

- **Notifier Worker** (`workers/notifier/`)
  - Evaluates notification rules
  - Determines when and how to send notifications based on project settings

- **Accountant Worker** (`workers/accountant/`)
  - Processes accounting-related events
  - Integrates with the Accounting service for financial operations

- **Paymaster Worker** (`workers/paymaster/`)
  - Handles payment processing tasks
  - Manages subscription renewals and payment failures

- **Limiter Worker** (`workers/limiter/`)
  - Enforces rate limits and quotas
  - Tracks usage against plan limits
  - Generates reports for limit violations

- **Archiver Worker** (`workers/archiver/`)
  - Archives old events based on retention policies
  - Generates daily/weekly/monthly reports
  - Manages data lifecycle

- **Release Worker** (`workers/release/`)
  - Processes source map releases
  - Stores source maps for JavaScript error processing
  - Associates releases with error events

- **Sentry Worker** (`workers/sentry/`)
  - Converts Sentry envelope format to Hawk format
  - Processes Sentry-compatible error events

**Worker Infrastructure:**
- Base `Worker` class handles RabbitMQ connection and message consumption
- Automatic retry logic for failed messages
- Support for concurrent task processing (`SIMULTANEOUS_TASKS`)
- Integrated logging with Winston
- Cache controller for performance optimization
- MongoDB database controller for data persistence

#### 4. API (`api/`)

**Technology:** Node.js/TypeScript, GraphQL (Apollo Server), Express  
**Purpose:** Main GraphQL API for frontend and external integrations

The API service provides a comprehensive GraphQL interface for:

**Core Entities:**
- **Users** - User authentication, profiles, preferences
- **Workspaces** - Organization-level containers for projects
- **Projects** - Error tracking projects with settings and integrations
- **Events** - Error events with filtering, grouping, and search
- **Notifications** - Notification rules and preferences
- **Billing** - Payment processing, subscriptions, invoices

**Key Features:**
- GraphQL schema with type definitions and resolvers
- JWT-based authentication
- Role-based access control (admin, workspace member, etc.)
- File upload support for images and attachments
- Integration with Accounting service for billing
- Metrics endpoint for Prometheus monitoring
- GraphQL Playground and Voyager for schema exploration

**Database:**
- MongoDB for primary data storage
- Separate databases for accounts and events
- Migration support with `migrate-mongo`

#### 5. Garage (`garage/`)

**Technology:** Vue.js 3, TypeScript, Vite  
**Purpose:** Main web application frontend

Garage is the primary user interface for Hawk, providing:
- Project and workspace management
- Error event visualization and filtering
- User authentication and authorization
- Billing and subscription management
- Notification settings
- Source map management
- Real-time error monitoring dashboards

**Features:**
- Vue 3
- Vuex
- GraphQL client integration
- Component library with Storybook

#### 6. Yard (`yard/`)

**Technology:** Nuxt.js  
**Purpose:** Marketing and landing pages

Yard serves as the public-facing website for Hawk, including:
- Product landing pages
- Documentation
- Marketing content
- Public API documentation

#### 7. Accounting (`accounting/`)

**Technology:** Node.js/TypeScript, GraphQL  
**Purpose:** Financial accounting microservice

The Accounting service handles:
- Double-entry bookkeeping
- Cashbook and revenue account management
- Financial transaction recording
- Integration with payment processors

**Database:**
- Separate MongoDB database for accounting data
- Migration support for schema changes

#### 8. Cron Manager (`cron-manager/`)

**Technology:** Node.js/TypeScript  
**Purpose:** Scheduled task scheduler

Cron Manager schedules periodic tasks and publishes them to RabbitMQ:
- Daily/weekly/monthly reports
- Data archival jobs
- Limit checking tasks
- Subscription renewal reminders

**Configuration:**
- YAML-based configuration file
- Flexible scheduling with cron expressions

### Client SDKs (Catchers)

#### JavaScript Catcher (`catchers/javascript/`)

**Technology:** TypeScript  
**Purpose:** Browser and Node.js error tracking SDK

Features:
- Automatic global error handling
- Vue.js integration
- React support
- Source map support
- Custom context and user tracking
- Before-send hooks for data filtering
- Manual error reporting API

#### Node.js Catcher (`catchers/nodejs/`)

**Technology:** TypeScript  
**Purpose:** Server-side Node.js error tracking

Features:
- Express middleware integration
- Unhandled promise rejection tracking
- Process error handling
- Custom context support

#### PHP Catcher (`catchers/php/`)

**Technology:** PHP  
**Purpose:** PHP application error tracking

Features:
- Exception handler integration
- Laravel support
- Custom error reporting

### Shared Components

#### Types (`types/`)

**Technology:** TypeScript  
**Purpose:** Shared type definitions

Contains TypeScript type definitions used across multiple services:
- Event payload types
- API response types
- Worker task types
- Database model types

## Data Flow

### Error Collection Flow

1. **Client Application** → **Collector**
   - Client SDK (catcher) sends error event via HTTP/WebSocket
   - Event includes JWT token and error payload

2. **Collector Processing**
   - Validates JWT token and extracts project ID
   - Checks rate limits using Redis
   - Validates IP against blacklist
   - Determines target queue based on catcher type

3. **Collector** → **RabbitMQ (Registry)**
   - Publishes validated event to `errors` exchange
   - Exchange routes to appropriate queue (`errors/javascript`, `errors/default`, etc.)

4. **Worker Processing**
   - Worker consumes message from queue
   - Processes event (formatting, source map application, grouping, etc.)
   - Saves to MongoDB
   - Publishes notification tasks if needed

5. **Notification Flow**
   - Notification workers consume tasks from `log` queue
   - Send emails, Telegram messages, Slack notifications
   - Respect user notification preferences

### Source Map Flow

1. **Build Process** → **Collector**
   - CI/CD pipeline uploads source map via `POST /release`
   - Includes release identifier, source map file, and commit information

2. **Collector** → **RabbitMQ**
   - Publishes to `release` exchange

3. **Release Worker**
   - Processes source map
   - Stores in database/storage
   - Associates with release identifier

4. **Error Processing**
   - When JavaScript error occurs, JavaScript worker retrieves source map
   - Applies transformation to unminify stack trace
   - Stores original source locations in event

### User Interaction Flow

1. **User** → **Garage (Frontend)**
   - User interacts with Vue.js application

2. **Garage** → **API (GraphQL)**
   - Frontend makes GraphQL queries/mutations
   - Authenticates using JWT tokens

3. **API** → **MongoDB**
   - Resolvers fetch/update data from database
   - Apply business logic and authorization

4. **API** → **Garage**
   - Returns GraphQL responses
   - Frontend updates UI

## Infrastructure

### Databases

- **MongoDB** - Primary data store
  - `hawk` database - Accounts, users, workspaces, projects
  - `hawk_events` database - Error events and related data
  - Separate accounting database for financial data

- **Redis** - Caching and rate limiting
  - Project settings cache
  - Rate limit counters
  - IP blacklist
  - Disabled projects set

### Message Queue

- **RabbitMQ** - Message broker
  - Durable exchanges and queues
  - Dead-letter queues for error handling
  - Message persistence for reliability

### Monitoring

- **Prometheus** - Metrics collection
- **Pushgateway** - Metrics aggregation
- Custom metrics endpoints in services

## Deployment

The system could be deployed to any cloud provider.
For development and testing, it can be run in Docker containers with docker-compose:

- Each service has its own Dockerfile
- Shared volumes for development
- Network isolation between services
- Environment variable configuration
- Health check endpoints

## Security

- JWT-based authentication
- Token validation at Collector entry point
- Rate limiting to prevent abuse
- IP blacklisting for DDoS protection
- Role-based access control in API
- Secure password hashing (Argon2)
- CORS configuration for frontend

## Scalability

- Stateless services for horizontal scaling
- Message queue enables distributed processing
- Worker instances can be scaled independently
- Redis caching reduces database load
- MongoDB sharding support for large datasets

## Development

The monorepo structure allows:
- Shared code and types across services
- Unified development environment
- Coordinated versioning
- Simplified dependency management

Each service can be developed and tested independently while maintaining integration through shared interfaces and message protocols.

