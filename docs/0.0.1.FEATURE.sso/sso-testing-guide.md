# SSO Testing Guide

This guide explains how to test Hawk's SSO implementation using Keycloak as IdP.

## Prerequisites

- Docker and Docker Compose installed
- All services from main docker-compose.yml running

## Quick Start

### 1. Start Keycloak

From the project root:

```bash
docker-compose up -d keycloak
```

Wait for Keycloak to start (check logs):

```bash
docker-compose logs -f keycloak
```

Keycloak will be available at: **http://localhost:8180**

### 2. Setup Keycloak

Run the setup script to create realm, client, and test users.

**Option 1: From your host machine** (recommended):

```bash
cd api/test/integration/keycloak
KEYCLOAK_URL=http://localhost:8180 ./setup.sh
```

**Option 2: From API container** (if curl not available on host):

```bash
docker-compose exec -e KEYCLOAK_URL=http://keycloak:8180 api /keycloak/setup.sh
```

**Note:** The script requires `curl` and `bash` which are not available in the Keycloak container. Run from host or from another container that has these tools (like `api`).

The script will output:
- Admin console URL and credentials
- Test user credentials
- SSO configuration URLs
- X.509 certificate location

### 3. Configure SSO in Hawk

#### Get Configuration Values

- Go to: Realm Settings → Keys → RS256 → Certificate
- Copy the certificate (without BEGIN/END lines)

#### Configure in Hawk UI

1. Open Hawk workspace settings → SSO
2. Enable SSO
3. Fill in the configuration:
   - **IdP Entity ID**: `http://localhost:8180/realms/hawk`
   - **SSO URL**: `http://localhost:8180/realms/hawk/protocol/saml`
   - **X.509 Certificate**: Use value from step above
   - **Name ID Format**: Email address
   - **Attribute Mapping**:
     - Email: `email`
     - Name: `name` (full name)
4. Save configuration

### 4. Test SSO Login

#### Manual Test

1. Navigate to: `http://localhost:4000/login/sso/{workspaceId}`
2. You'll be redirected to Keycloak login page
3. Login with test user credentials:
   - Email: `testuser@hawk.local`
   - Password: `password123`
4. After successful authentication, you'll be redirected back to Hawk
5. Check that you're logged in

#### Test Users

| Username | Email | Password | Department | Title |
|----------|-------|----------|------------|-------|
| testuser | testuser@hawk.local | password123 | Engineering | Software Engineer |
| alice | alice@hawk.local | password123 | Product | Product Manager |
| bob | bob@hawk.local | password123 | Engineering | Senior Developer |

#### Automated Test

Run integration tests (all services start automatically in Docker):

```bash
cd api
yarn test:integration
```

This command will:
1. ✅ Start MongoDB, RabbitMQ, Keycloak, and API in Docker
2. ✅ Wait for all services to be ready
3. ✅ Configure Keycloak with test realm and users
4. ✅ Run SSO integration tests
5. ✅ Clean up containers after tests complete

**Note:** First run may take a few minutes to download Docker images and build containers.

## Keycloak Admin Console

Access Keycloak admin console at: **http://localhost:8180**

- Username: `admin`
- Password: `admin`

### Useful Admin Tasks

#### View SAML Metadata

```bash
curl http://localhost:8180/realms/hawk/protocol/saml/descriptor
```

#### View/Edit Users

1. Go to: Users → View all users
2. Select user to edit attributes
3. Click "Save"

#### View/Edit SAML Client

1. Go to: Clients → hawk-sp
2. Edit settings as needed
3. View/regenerate keys and certificates

#### View SAML Assertions

1. Go to: Clients → hawk-sp → Client Scopes
2. View configured attributes and mappers

## Testing Different Scenarios

### Test JIT (Just-In-Time) Provisioning

1. Login with a user that doesn't exist in Hawk database
2. User should be automatically created
3. User should be added to the workspace

### Test SSO Enforcement

1. Enable "Enforce SSO" in workspace settings
2. Try to login with email/password → Should be blocked
3. Try to login with SSO → Should work

### Test Token Lifetime

1. Login via SSO with enforced workspace
2. Check refresh token expiry → Should be 2 days
3. Login with regular email/password (different workspace)
4. Check refresh token expiry → Should be 30 days

### Test SAML Attributes

1. Update user attributes in Keycloak admin console
2. Login via SSO
3. Check that attributes are correctly mapped to Hawk user

## Cleanup

### Stop Keycloak

```bash
docker-compose stop keycloak
```

### Remove Keycloak data

```bash
docker volume rm hawk-mono_keycloak-data
```

or

```bash
docker-compose down -v
# This will remove ALL volumes, including MongoDB data
```

### Reset Keycloak configuration

1. Stop Keycloak
2. Remove volume
3. Start Keycloak
4. Run setup script again


## CI/CD Integration

For CI/CD pipelines, use docker-compose.test.yml:

```yaml
# .github/workflows/test.yml
- name: Run integration tests
  run: |
    docker-compose -f api/docker-compose.test.yml up --build --exit-code-from tests tests
```

The test suite will:
1. Start Keycloak
2. Wait for Keycloak to be ready
3. Configure realm via API
4. Run integration tests
5. Cleanup

## References

- [SSO in Hawk](./sso.md)
- [SSO Implementation Plan](./sso-implementation.md)
- [Keycloak Setup Guide](../api/docs/keycloak.md)
- [Keycloak Documentation](https://www.keycloak.org/documentation)
- [SAML 2.0 Specification](https://www.oasis-open.org/standards#samlv2.0)
