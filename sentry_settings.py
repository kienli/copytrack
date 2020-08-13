import sentry_sdk
from sentry_sdk.integrations.rq import RqIntegration

sentry_sdk.init("https://sentry_url", integrations=[RqIntegration()])
