"""AgentArts Runtime connectivity check for the phase-two Crossref gateway."""

import asyncio
import os
from types import SimpleNamespace
from urllib.request import build_opener

from agentarts.sdk import AgentArtsRuntimeApp, AgentArtsRuntimeContext, IdentityClient
from agentarts.sdk.utils.metadata import MetadataProvider

from probe_gateway_mcp import BlockRedirects, GatewayProbe, ProbeError, V11ProbeSigner, search_once

app = AgentArtsRuntimeApp()


def runtime_credentials():
    provider = os.environ.get("GATEWAY_STS_PROVIDER", "").strip()
    if not provider:
        try:
            credentials = MetadataProvider().get_credentials()
            return credentials.ak, credentials.sk, credentials.security_token
        except Exception:
            raise ProbeError("metadata_credentials_unavailable") from None

    workload_token = AgentArtsRuntimeContext.get_workload_access_token()
    if not workload_token:
        raise ProbeError("workload_token_missing")
    try:
        credentials = IdentityClient(region="cn-southwest-2").get_resource_sts_token(
            provider_name=provider,
            workload_access_token=workload_token,
            agency_session_name="literature-runtime-probe",
        )
        return credentials.access_key_id, credentials.secret_access_key, credentials.security_token
    except Exception:
        raise ProbeError("sts_exchange_failed") from None


def run_gateway_search(query, credentials):
    access_key, secret_key, security_token = credentials
    probe = GatewayProbe(
        V11ProbeSigner(access_key, secret_key),
        SimpleNamespace,
        build_opener(BlockRedirects()),
        security_token,
    )
    probe.connect()
    return search_once(probe, query)


@app.entrypoint
async def invoke(payload: dict) -> dict:
    raw_query = payload.get("query") if isinstance(payload, dict) else None
    query = raw_query.strip() if isinstance(raw_query, str) else ""
    if not 1 <= len(query) <= 200:
        return {"status": "error", "stage": "input", "code": "invalid_query"}

    try:
        credentials = await asyncio.to_thread(runtime_credentials)
    except ProbeError as error:
        return {"status": "error", "stage": "identity", "code": str(error)}
    if not all(isinstance(value, str) and value.strip() for value in credentials):
        return {"status": "error", "stage": "identity", "code": "runtime_credentials_incomplete"}

    try:
        papers = await asyncio.to_thread(run_gateway_search, query, credentials)
    except ProbeError as error:
        return {"status": "error", "stage": "gateway", "diagnostic": str(error)}
    except (KeyError, TypeError, ValueError, AttributeError):
        return {"status": "error", "stage": "gateway", "code": "invalid_gateway_response"}

    return {"status": "ok", "scope": "runtime_gateway_probe", "papers": papers}
