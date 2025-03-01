import sentry_sdk
import os

HAWK_INTEGRATION_TOKEN = os.getenv("SENTRY_PROJECT_ID", "eyJpbnRlZ3JhdGlvbklkIjoiOWQ0MzUwMzgtMWQ3OS00NTlhLWJhMWUtZWQwMDVjYzI0NTM0Iiwic2VjcmV0IjoiZGU3ODZkMDAtNzE2Ni00ZTYzLWI5YzAtYTFjNjcyOWZlOGU5In0=")

sentry_sdk.init(
    dsn=f"http://{HAWK_INTEGRATION_TOKEN}@localhost:3000/0",
    debug=True
)
division_by_zero = 1 / 0
# raise Exception("This is a test exception")