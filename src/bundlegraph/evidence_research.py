"""Bounded, source-allowlisted evidence research without approval or purchase powers."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
import ipaddress
import socket
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .evidence_repository import EvidenceFreshnessPolicy, EvidenceLookup, EvidenceRecord, EvidenceRepository, RetrievalMode
from .models import ConflictStatus, Evidence, EvidenceSourceType, FreshnessStatus, Origin, SupportStatus


class ResearchStatus(StrEnum):
    EXISTING_EVIDENCE = "existing_evidence"
    EVIDENCE_CREATED = "evidence_created"
    UNKNOWN = "unknown"
    RESEARCH_FAILED = "research_failed"


class ResearchSecurityError(RuntimeError):
    pass


class ResearchProviderUnavailable(RuntimeError):
    pass


class ApprovedSourcePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    allowed_domains: frozenset[str] = Field(min_length=1)
    max_navigations: int = Field(default=2, ge=1, le=5)
    timeout_seconds: float = Field(default=10, gt=0, le=60)
    max_response_bytes: int = Field(default=200_000, ge=1_024, le=1_000_000)


class ResearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)
    product_id: str
    variant_id: str
    missing_attribute: str = Field(min_length=1)
    source_url: str = Field(min_length=1)


class PageCapture(BaseModel):
    model_config = ConfigDict(frozen=True)
    final_url: str
    text: str
    trace_reference: str


class ResearchExtraction(BaseModel):
    """The untrusted extractor can suggest a fact only; navigation stays outside it."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    attribute: str = Field(min_length=1)
    normalized_value: str | int | float | bool | None
    excerpt: str = Field(min_length=1, max_length=4_000)


class ResearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: ResearchStatus
    request: ResearchRequest
    evidence_id: str | None = None
    trace_references: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    retrieval_mode: RetrievalMode | None = None
    compatibility_trace_reference: str | None = None


class KernelSession(Protocol):
    def fetch(self, url: str, *, timeout_seconds: float, max_response_bytes: int) -> PageCapture: ...
    def close(self) -> None: ...


class KernelSessionFactory(Protocol):
    def open_session(self, policy: ApprovedSourcePolicy) -> KernelSession: ...


class AstropodsResearchExecutor(Protocol):
    def extract(self, *, page_text: str, attribute: str) -> Mapping[str, Any]: ...


class CompatibilityRerunner(Protocol):
    def rerun(self, product_id: str, variant_id: str) -> str: ...


def _public_host(url: str, *, resolver: Callable[[str, int | None], list[tuple[Any, ...]]] = socket.getaddrinfo) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ResearchSecurityError("RESEARCH_DESTINATION_DISALLOWED")
    host = parsed.hostname.rstrip(".").lower()
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addresses = [ipaddress.ip_address(item[4][0]) for item in resolver(host, None)]
        except OSError as error:
            raise ResearchSecurityError("RESEARCH_DESTINATION_UNRESOLVED") from error
    if not addresses or any(address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_unspecified for address in addresses):
        raise ResearchSecurityError("RESEARCH_DESTINATION_DISALLOWED")
    return host


class BoundedKernelSession:
    """Validates initial and redirected destinations at the request boundary."""

    def __init__(self, session: KernelSession, policy: ApprovedSourcePolicy, *, resolver: Callable[[str, int | None], list[tuple[Any, ...]]] = socket.getaddrinfo) -> None:
        self._session, self._policy, self._resolver, self._navigations = session, policy, resolver, 0

    def fetch(self, url: str) -> PageCapture:
        self._validate(url)
        if self._navigations >= self._policy.max_navigations:
            raise ResearchSecurityError("RESEARCH_NAVIGATION_BUDGET_EXCEEDED")
        self._navigations += 1
        page = self._session.fetch(url, timeout_seconds=self._policy.timeout_seconds, max_response_bytes=self._policy.max_response_bytes)
        self._validate(page.final_url)
        if len(page.text.encode("utf-8")) > self._policy.max_response_bytes:
            raise ResearchSecurityError("RESEARCH_RESPONSE_BUDGET_EXCEEDED")
        return page

    def _validate(self, url: str) -> None:
        host = _public_host(url, resolver=self._resolver)
        if not any(host == domain or host.endswith(f".{domain}") for domain in self._policy.allowed_domains):
            raise ResearchSecurityError("RESEARCH_DESTINATION_DISALLOWED")

    def close(self) -> None:
        self._session.close()


class KernelUnavailableFactory:
    """Live KERNEL SDK wiring is deliberately unavailable until credentials are configured."""

    def open_session(self, policy: ApprovedSourcePolicy) -> KernelSession:
        raise ResearchProviderUnavailable("KERNEL SDK and KERNEL_API_KEY are not configured")


class AstropodsUnavailableExecutor:
    def extract(self, *, page_text: str, attribute: str) -> Mapping[str, Any]:
        raise ResearchProviderUnavailable("Astropods agent/runtime is not configured")


class EvidenceResearchWorkflow:
    def __init__(self, repository: EvidenceRepository, sessions: KernelSessionFactory, executor: AstropodsResearchExecutor, rerunner: CompatibilityRerunner, policy: ApprovedSourcePolicy, *, now: Callable[[], datetime] = lambda: datetime.now(UTC), resolver: Callable[[str, int | None], list[tuple[Any, ...]]] = socket.getaddrinfo) -> None:
        self._repository, self._sessions, self._executor, self._rerunner, self._policy, self._now, self._resolver = repository, sessions, executor, rerunner, policy, now, resolver

    def research(self, request: ResearchRequest) -> ResearchResult:
        existing = self._repository.lookup(EvidenceLookup(product_id=request.product_id, variant_id=request.variant_id, attribute=request.missing_attribute), as_of=self._now(), freshness=EvidenceFreshnessPolicy())
        if existing.matches:
            status = ResearchStatus.UNKNOWN if existing.conflicting_values else ResearchStatus.EXISTING_EVIDENCE
            return ResearchResult(status=status, request=request, trace_references=tuple(match.record.evidence.evidence_id for match in existing.matches), reason_codes=("CONFLICTING_EVIDENCE",) if existing.conflicting_values else (), retrieval_mode=existing.mode)
        session: BoundedKernelSession | None = None
        try:
            session = BoundedKernelSession(self._sessions.open_session(self._policy), self._policy, resolver=self._resolver)
            page = session.fetch(request.source_url)
            try:
                extraction = ResearchExtraction.model_validate(self._executor.extract(page_text=page.text, attribute=request.missing_attribute))
            except ValidationError:
                return ResearchResult(status=ResearchStatus.RESEARCH_FAILED, request=request, trace_references=(page.trace_reference,), reason_codes=("RESEARCH_OUTPUT_SCHEMA_INVALID",))
            if extraction.attribute != request.missing_attribute or extraction.normalized_value is None:
                return ResearchResult(status=ResearchStatus.UNKNOWN, request=request, trace_references=(page.trace_reference,), reason_codes=("REQUESTED_FACT_NOT_FOUND",))
            evidence_id = f"research-{request.product_id}-{request.variant_id}-{request.missing_attribute}".replace("_", "-")
            evidence = Evidence(evidence_id=evidence_id, subject_id=request.product_id, attribute=request.missing_attribute, observed_value=extraction.normalized_value, source_url=page.final_url, source_type=EvidenceSourceType.MANUFACTURER, observed_at=self._now(), excerpt=extraction.excerpt, origin=Origin.LIVE, support_status=SupportStatus.SUPPORTED, freshness_status=FreshnessStatus.FRESH, conflict_status=ConflictStatus.NONE)
            self._repository.ingest((EvidenceRecord(product_id=request.product_id, variant_id=request.variant_id, evidence=evidence),))
            check = self._repository.lookup(EvidenceLookup(product_id=request.product_id, variant_id=request.variant_id, attribute=request.missing_attribute), as_of=self._now(), freshness=EvidenceFreshnessPolicy())
            compatibility_trace = self._rerunner.rerun(request.product_id, request.variant_id)
            status = ResearchStatus.UNKNOWN if check.conflicting_values else ResearchStatus.EVIDENCE_CREATED
            return ResearchResult(status=status, request=request, evidence_id=evidence_id, trace_references=(page.trace_reference, evidence_id), reason_codes=("CONFLICTING_EVIDENCE",) if check.conflicting_values else (), retrieval_mode=check.mode, compatibility_trace_reference=compatibility_trace)
        except ResearchSecurityError as error:
            return ResearchResult(status=ResearchStatus.RESEARCH_FAILED, request=request, reason_codes=(str(error),))
        except (ResearchProviderUnavailable, TimeoutError):
            return ResearchResult(status=ResearchStatus.RESEARCH_FAILED, request=request, reason_codes=("RESEARCH_PROVIDER_UNAVAILABLE",))
        finally:
            if session is not None:
                session.close()
