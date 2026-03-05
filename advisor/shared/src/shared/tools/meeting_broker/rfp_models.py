"""Pydantic response models for the RFP API.

All models use ``extra="allow"`` so that new API fields never break parsing.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

_cfg = ConfigDict(populate_by_name=True, extra="allow")


class RfpBase(BaseModel):
    model_config = _cfg


# ── Shared primitives ─────────────────────────────────────────────────────────

class PersonSummary(RfpBase):
    id: str | None = None
    name: str | None = None


class Channel(RfpBase):
    id: str | None = None
    name: str | None = None
    isEditable: bool | None = None


class Reference(RfpBase):
    id: str | None = None
    resourceType: str | None = None


class Answer(RfpBase):
    responseText: str | None = None
    responseUnits: str | None = None
    responses: list[Any] | None = None


class Question(RfpBase):
    id: str | None = None
    answer: Answer | None = None
    questionText: str | None = None
    type: str | None = None
    category: str | None = None
    section: str | None = None


class AdditionalInfo(RfpBase):
    Type: str | None = None
    Name: str | None = None
    Category: str | None = None
    Value: str | None = None


class TeamMember(RfpBase):
    person: PersonSummary | None = None
    assignmentMethod: str | None = None
    role: dict[str, Any] | None = None


class ProposalProvider(RfpBase):
    id: str | None = None
    name: str | None = None
    proposalUrl: str | None = None


class StatusCount(RfpBase):
    name: str | None = None
    value: str | None = None


class StatusRevenue(RfpBase):
    name: str | None = None
    actualRevenue: float | None = None
    forecastRevenue: float | None = None


class KeyValuePairModel(RfpBase):
    key: str | None = None
    value: str | None = None


class SnapshotField(RfpBase):
    type: str | None = None
    fieldName: str | None = None
    oldText: str | None = None
    newText: str | None = None


class SnapshotSection(RfpBase):
    sectionName: str | None = None
    type: str | None = None
    fields: list[SnapshotField] | None = None


# ── RFP Summary (search results) ──────────────────────────────────────────────

class RfpSummary(RfpBase):
    id: str | None = None
    status: str | None = None
    meetingName: str | None = None
    ownerName: str | None = None
    ownerId: str | None = None
    accountName: str | None = None
    accountId: str | None = None
    agencyName: str | None = None
    contactName: str | None = None
    arrivalDate: str | None = None
    receivedDate: str | None = None
    budget: float | None = None
    rate: float | None = None
    proposalSentDate: str | None = None
    rfpMilestone: str | None = None
    rfpMilestoneTypeId: int | None = None
    milestoneStatusChangeDate: str | None = None
    nextStepId: int | None = None
    nextStepName: str | None = None
    nextStepDueDate: str | None = None
    nextStepGuid: str | None = None


# ── RFP Detail ────────────────────────────────────────────────────────────────

class RfpMilestone(RfpBase):
    rfpStatusMilestoneId: int | None = None
    rfpStatusMilestoneName: str | None = None
    rfpMilestoneTypeId: int | None = None
    milestoneStatusChangeDate: str | None = None


class RfpNextStep(RfpBase):
    nextStepId: int | None = None
    nextStepGuid: str | None = None
    nextStepName: str | None = None
    nextStepDueDate: str | None = None


class RfpDetails(RfpBase):
    id: str | None = None
    externalId: str | None = None
    internalId: str | None = None
    owner: PersonSummary | None = None
    channel: Channel | None = None
    rfpMilestone: RfpMilestone | None = None
    rfpNextStep: RfpNextStep | None = None


# ── Team ──────────────────────────────────────────────────────────────────────

class Team(RfpBase):
    id: str | None = None
    parentId: str | None = None
    members: list[TeamMember] | None = None


# ── Typed response wrappers ───────────────────────────────────────────────────

class SearchRfpData(RfpBase):
    rfpSummaries: list[RfpSummary] | None = None
    totalCount: int | None = None
    continuationToken: str | None = None


class SearchRfpResponse(RfpBase):
    data: SearchRfpData | None = None
    meta: dict[str, Any] | None = None


class RfpDetailData(RfpBase):
    rfp: RfpDetails | None = None


class GetRfpResponse(RfpBase):
    data: RfpDetailData | None = None


class StatusCountsData(RfpBase):
    statusCounts: list[StatusCount] | None = None


class StatusCountsResponse(RfpBase):
    data: StatusCountsData | None = None


class StatusRevenueData(RfpBase):
    statusRevenues: list[StatusRevenue] | None = None


class StatusRevenueResponse(RfpBase):
    data: StatusRevenueData | None = None


class QuestionsData(RfpBase):
    questions: list[Question] | None = None


class QuestionsResponse(RfpBase):
    data: QuestionsData | None = None


class AdditionalInfoData(RfpBase):
    additionalInfo: list[AdditionalInfo] | None = None


class AdditionalInfoResponse(RfpBase):
    data: AdditionalInfoData | None = None


class TeamData(RfpBase):
    team: Team | None = None
    continuationToken: str | None = None
    totalCount: int | None = None


class TeamResponse(RfpBase):
    data: TeamData | None = None


class ProposalProvidersData(RfpBase):
    proposalProviders: list[ProposalProvider] | None = None


class ProposalProvidersResponse(RfpBase):
    data: ProposalProvidersData | None = None


class PutData(RfpBase):
    reference: Reference | None = None


class PutResponse(RfpBase):
    data: PutData | None = None


class UpdateQuestionsData(RfpBase):
    questions: list[Question] | None = None


class UpdateQuestionsResponse(RfpBase):
    data: UpdateQuestionsData | None = None


class TeamMemberData(RfpBase):
    id: str | None = None


class TeamMemberResponse(RfpBase):
    data: TeamMemberData | None = None


class SnapshotsData(RfpBase):
    kvpCollection: list[KeyValuePairModel] | None = None


class SnapshotsResponse(RfpBase):
    data: SnapshotsData | None = None


class SnapshotDetailsData(RfpBase):
    sections: list[SnapshotSection] | None = None


class SnapshotDetailsResponse(RfpBase):
    data: SnapshotDetailsData | None = None


class NoContentResponse(RfpBase):
    """Returned for 204 No Content responses."""

    success: bool = True
