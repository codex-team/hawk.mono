import sentry_sdk
import os

HAWK_INTEGRATION_TOKEN = os.getenv("SENTRY_PROJECT_ID", "eyJpbnRlZ3JhdGlvbklkIjoiYzlmZTY1MzYtYjVkYi00NDNmLWI1MmEtMWQwNDY1OThkNDNiIiwic2VjcmV0IjoiNzAwZTAwYTQtM2E4Mi00NTQ3LTkzOGUtMTMzMGJhNzgwY2UwIn0=")

sentry_sdk.init(
    dsn=f"http://{HAWK_INTEGRATION_TOKEN}@localhost:3000/0",
    debug=True
)
division_by_zero = 1 / 0