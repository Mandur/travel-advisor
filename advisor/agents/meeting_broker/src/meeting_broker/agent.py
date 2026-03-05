"""Meeting broker agent — wraps the RFP API as agent tools."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from agent_framework import Agent, tool
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

from shared.config import get_config
from shared.utils import setup_logging
from shared.tools.meeting_broker.rfp_client import RfpApiClient
from shared.tools.meeting_broker.rfp_models import (
    AdditionalInfoResponse,
    GetRfpResponse,
    NoContentResponse,
    ProposalProvidersResponse,
    PutResponse,
    QuestionsResponse,
    SearchRfpResponse,
    SnapshotDetailsResponse,
    SnapshotsResponse,
    StatusCountsResponse,
    StatusRevenueResponse,
    TeamMemberResponse,
    TeamResponse,
    UpdateQuestionsResponse,
)

logger = setup_logging("meeting-broker-agent")

MEETING_BROKER_INSTRUCTIONS = """You are an RFP (Request for Proposal) management agent for a hospitality platform.
You search, retrieve, and manage RFPs for meetings and events on behalf of the user.

Your capabilities:
- Search and filter RFPs by name, account, status, dates, milestone, and more
- Retrieve full RFP details including questions, team, additional information, and snapshots
- Update RFP content, status, and ownership
- Manage RFP team members (add, update, remove)
- Retrieve proposal providers associated with an RFP
- Compare RFP snapshots to see what changed over time

Always use the available tools to answer RFP questions accurately."""


@lru_cache(maxsize=1)
def _client() -> RfpApiClient:
    return RfpApiClient()


# ── Search & retrieve ─────────────────────────────────────────────────────────


@tool
def search_rfps(
    meeting_name: str | None = None,
    account_name: str | None = None,
    status: str | None = None,
    arrival_date: str | None = None,
    received_date: str | None = None,
    total_budget: str | None = None,
    rate: str | None = None,
    proposal_sent_date: str | None = None,
    external_rfp_id: str | None = None,
    internal_id: str | None = None,
    location_name: str | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
    rfp_milestone: str | None = None,
    next_step_name: str | None = None,
    next_step_due_date: str | None = None,
    continuation_token: str | None = None,
    is_next_step_overdue: bool | None = None,
    is_export: bool | None = None,
) -> dict:
    """Search and retrieve a list of RFPs matching the supplied filters.

    All parameters are optional — omit any you do not need.

    Args:
        meeting_name: Partial name of the meeting to search for.
        account_name: Name of the enterprise the RFP was created for.
        status: RFP status string (e.g. "New", "Awarded", "TurnedDown").
        arrival_date: Meeting arrival date in YYYYMMDD format.
        received_date: Date the RFP was received in YYYYMMDD format.
        total_budget: Total budget filter.
        rate: Guest room rate filter.
        proposal_sent_date: Date the proposal was first sent.
        external_rfp_id: External RFP identifier.
        internal_id: Integer identifier for the RFP.
        location_name: Name of the receiving location.
        limit: Maximum number of results to return.
        sort_by: Column to sort results by.
        rfp_milestone: Milestone type name (e.g. "Published", "Viewed").
        next_step_name: Partial name of the next step action.
        next_step_due_date: Due date for the next step in YYYYMMDD format.
        continuation_token: Token for the next page of results.
        is_next_step_overdue: Filter to only overdue next steps when True.
        is_export: Set to True when exporting results to a file.

    Returns:
        Typed SearchRfpResponse with a list of RFP summaries and total count.
    """
    raw = _client().get(
        "/rfps",
        params={
            "meetingName": meeting_name,
            "accountName": account_name,
            "status": status,
            "arrivalDate": arrival_date,
            "receivedDate": received_date,
            "totalBudget": total_budget,
            "rate": rate,
            "proposalSentDate": proposal_sent_date,
            "externalRfpId": external_rfp_id,
            "internalId": internal_id,
            "locationName": location_name,
            "limit": limit,
            "sortBy": sort_by,
            "rfpMilestone": rfp_milestone,
            "nextStepName": next_step_name,
            "nextStepDueDate": next_step_due_date,
            "continuationToken": continuation_token,
            "isNextStepOverdue": is_next_step_overdue,
            "isExport": is_export,
        },
    )
    return SearchRfpResponse.model_validate(raw).model_dump(mode="json")


@tool
def get_rfp(rfp_id: str, children: str | None = None) -> dict:
    """Retrieve full details for a single RFP by its GUID.

    Args:
        rfp_id: UUID of the RFP to retrieve.
        children: Comma-separated list of child nodes to include (e.g. "questions,team").

    Returns:
        Typed GetRfpResponse with the full RFP detail object.
    """
    raw = _client().get(f"/rfps/{rfp_id}", params={"children": children})
    return GetRfpResponse.model_validate(raw).model_dump(mode="json")


@tool
def get_rfp_status_counts(
    start_date: str | None = None,
    end_date: str | None = None,
    statuses: str | None = None,
    location_ids: str | None = None,
) -> dict:
    """Retrieve the count of RFPs grouped by status for a date range.

    Args:
        start_date: Start of the date range in YYYYMMDD format.
        end_date: End of the date range in YYYYMMDD format.
        statuses: Comma-delimited list of status names to filter by.
        location_ids: Comma-delimited list of location IDs to restrict counts to.

    Returns:
        Typed StatusCountsResponse with per-status counts.
    """
    raw = _client().get(
        "/rfps/status-counts",
        params={
            "startDate": start_date,
            "endDate": end_date,
            "statuses": statuses,
            "locationIds": location_ids,
        },
    )
    return StatusCountsResponse.model_validate(raw).model_dump(mode="json")


@tool
def get_rfp_status_revenues(
    start_date: str | None = None,
    end_date: str | None = None,
    statuses: str | None = None,
    is_actual: bool | None = None,
    location_ids: str | None = None,
) -> dict:
    """Retrieve RFP revenue figures grouped by status for a date range.

    Args:
        start_date: Start of the date range in YYYYMMDD format.
        end_date: End of the date range in YYYYMMDD format.
        statuses: Comma-delimited list of RFP status names to include.
        is_actual: True for actual revenue totals; False (default) for forecast.
        location_ids: Comma-delimited list of location IDs to filter by.

    Returns:
        Typed StatusRevenueResponse with revenue per status.
    """
    raw = _client().get(
        "/rfps/status-revenues",
        params={
            "startDate": start_date,
            "endDate": end_date,
            "statuses": statuses,
            "isActual": is_actual,
            "locationIds": location_ids,
        },
    )
    return StatusRevenueResponse.model_validate(raw).model_dump(mode="json")


@tool
def get_rfp_questions(rfp_id: str) -> dict:
    """Retrieve the questions and answers associated with an RFP.

    Args:
        rfp_id: UUID of the RFP.

    Returns:
        Typed QuestionsResponse with the list of questions and their answers.
    """
    raw = _client().get(f"/rfps/{rfp_id}/questions")
    return QuestionsResponse.model_validate(raw).model_dump(mode="json")


@tool
def get_rfp_additional_information(rfp_id: str) -> dict:
    """Retrieve the additional information fields attached to an RFP.

    Args:
        rfp_id: UUID of the RFP.

    Returns:
        Typed AdditionalInfoResponse with extra key/value fields.
    """
    raw = _client().get(f"/rfps/{rfp_id}/additional-information")
    return AdditionalInfoResponse.model_validate(raw).model_dump(mode="json")


@tool
def get_rfp_team(
    rfp_id: str,
    limit: int | None = None,
    continuation_token: str | None = None,
) -> dict:
    """Retrieve the team members assigned to an RFP.

    Args:
        rfp_id: UUID of the RFP.
        limit: Maximum number of team members to return (default 100).
        continuation_token: Token for the next page of results.

    Returns:
        Typed TeamResponse with team members and total count.
    """
    raw = _client().get(
        f"/rfps/{rfp_id}/team",
        params={"limit": limit, "continuationToken": continuation_token},
    )
    return TeamResponse.model_validate(raw).model_dump(mode="json")


@tool
def get_rfp_proposal_providers(rfp_id: str, channel_id: int | None = None) -> dict:
    """Retrieve the list of proposal providers associated with an RFP.

    Args:
        rfp_id: UUID of the RFP.
        channel_id: Optional channel integer ID; when provided the response
            includes the actual third-party proposal URL for that channel.

    Returns:
        Typed ProposalProvidersResponse with the provider list.
    """
    raw = _client().get(
        f"/rfps/{rfp_id}/proposal-providers",
        params={"channelId": channel_id},
    )
    return ProposalProvidersResponse.model_validate(raw).model_dump(mode="json")


@tool
def get_rfp_snapshots(rfp_id: str) -> dict:
    """Retrieve the list of available snapshots (historical versions) for an RFP.

    Args:
        rfp_id: UUID of the RFP.

    Returns:
        Typed SnapshotsResponse with snapshot IDs and version labels.
    """
    raw = _client().get(f"/rfps/{rfp_id}/snapshots")
    return SnapshotsResponse.model_validate(raw).model_dump(mode="json")


@tool
def get_rfp_snapshot_details(rfp_id: str, snapshot_id: int | None = None) -> dict:
    """Compare an RFP snapshot against the current version field-by-field.

    Args:
        rfp_id: UUID of the RFP.
        snapshot_id: Integer ID of the snapshot to compare.  Use
            ``get_rfp_snapshots`` to discover available snapshot IDs.

    Returns:
        Typed SnapshotDetailsResponse with sections of changed fields.
    """
    raw = _client().get(
        f"/rfps/{rfp_id}/compare-side-by-side",
        params={"snapshotId": snapshot_id},
    )
    return SnapshotDetailsResponse.model_validate(raw).model_dump(mode="json")


# ── Write operations ──────────────────────────────────────────────────────────


@tool
def update_rfp(rfp_id: str, rfp_details: dict[str, Any]) -> dict:
    """Update the content of an existing RFP.

    Provide only the fields you want to change inside ``rfp_details``.
    The object is sent as ``{"data": rfp_details}`` to the API.

    Example ``rfp_details``::

        {
            "id": "<rfp-guid>",
            "meeting": {"name": "New meeting title"},
            "channel": {"id": "<channel-guid>"}
        }

    Args:
        rfp_id: UUID of the RFP to update.
        rfp_details: Partial or full RfpDetails object to apply.

    Returns:
        NoContentResponse with ``success: True`` on success.
    """
    _client().put(f"/rfps/{rfp_id}", json={"data": rfp_details})
    return NoContentResponse().model_dump(mode="json")


@tool
def update_rfp_status(
    rfp_id: str,
    status: str,
    comment: str | None = None,
    start_date: str | None = None,
    reason_id: str | None = None,
) -> dict:
    """Change the status of an RFP and optionally record business data.

    Valid status values include: ``New``, ``Declined``, ``Awarded``,
    ``TurnedDown``, ``Cancelled``, ``Responded``, ``Viewed``, ``Published``.

    Args:
        rfp_id: UUID of the RFP.
        status: Target RFP status string.
        comment: Optional comment to record with the status change.
        start_date: Optional business data start date (ISO-8601 string).
        reason_id: Optional lost-business reason ID.

    Returns:
        Typed PutResponse with a reference to the updated RFP.
    """
    body: dict[str, Any] = {
        "data": {
            "rfpStatusChange": {
                "status": status,
                **({"comment": comment} if comment is not None else {}),
                **({"startDate": start_date} if start_date is not None else {}),
                **({"reasonId": reason_id} if reason_id is not None else {}),
            }
        }
    }
    raw = _client().put(f"/rfps/{rfp_id}/status", json=body)
    return PutResponse.model_validate(raw).model_dump(mode="json")


@tool
def reassign_rfp_owner(rfp_id: str, new_owner: dict[str, Any]) -> dict:
    """Reassign the owner of an RFP.

    ``new_owner`` should contain at minimum the new owner's ``id`` (UUID).
    Example::

        {"id": "<user-guid>"}

    Args:
        rfp_id: UUID of the RFP.
        new_owner: PersonSummary object identifying the new owner.

    Returns:
        Typed PutResponse with a reference to the updated RFP.
    """
    raw = _client().put(f"/rfps/{rfp_id}/owner", json={"data": {"owner": new_owner}})
    return PutResponse.model_validate(raw).model_dump(mode="json")


@tool
def update_rfp_question_answers(rfp_id: str, questions: list[dict[str, Any]]) -> dict:
    """Update the answers to one or more questions on an RFP.

    Each entry in ``questions`` should follow the Question schema.
    Provide either ``answer.responseText`` or ``answer.responses``::

        [
            {
                "id": "<question-id>",
                "answer": {"responseText": "Our answer here"}
            }
        ]

    Args:
        rfp_id: UUID of the RFP.
        questions: List of question objects with updated answers.

    Returns:
        Typed UpdateQuestionsResponse with the updated question list.
    """
    raw = _client().put(
        f"/rfps/{rfp_id}/questions/answers",
        json={"data": {"questions": questions}},
    )
    return UpdateQuestionsResponse.model_validate(raw).model_dump(mode="json")


@tool
def add_rfp_team_member(
    rfp_id: str,
    user_id: str,
    role_id: str | None = None,
) -> dict:
    """Add a member to the RFP team.

    Args:
        rfp_id: UUID of the RFP.
        user_id: UUID of the user to add.
        role_id: Optional UUID of the role to assign to the new member.

    Returns:
        Typed TeamMemberResponse with the new team member's ID.
    """
    member: dict[str, Any] = {"person": {"id": user_id}}
    if role_id is not None:
        member["role"] = {"id": role_id}
    raw = _client().post(f"/rfps/{rfp_id}/team/members", json={"data": member})
    return TeamMemberResponse.model_validate(raw).model_dump(mode="json")


@tool
def update_rfp_team_members(rfp_id: str, members: list[dict[str, Any]]) -> dict:
    """Update the team members of an RFP in bulk.

    Each entry should contain ``person``, ``assignmentMethod``, and ``role``
    fields mirroring the TeamMember schema.

    Args:
        rfp_id: UUID of the RFP.
        members: List of TeamMember objects with updated values.

    Returns:
        NoContentResponse with ``success: True`` on success.
    """
    _client().put(f"/rfps/{rfp_id}/team/members", json={"data": members})
    return NoContentResponse().model_dump(mode="json")


@tool
def remove_rfp_team_member(rfp_id: str, user_id: str) -> dict:
    """Remove a member from the RFP team.

    Args:
        rfp_id: UUID of the RFP.
        user_id: UUID of the team member to remove.

    Returns:
        NoContentResponse with ``success: True`` on success.
    """
    _client().delete(f"/rfps/{rfp_id}/team/members/{user_id}")
    return NoContentResponse().model_dump(mode="json")


# ── Agent factory ─────────────────────────────────────────────────────────────

_RFP_TOOLS = [
    search_rfps,
    get_rfp,
    get_rfp_status_counts,
    get_rfp_status_revenues,
    get_rfp_questions,
    get_rfp_additional_information,
    get_rfp_team,
    get_rfp_proposal_providers,
    get_rfp_snapshots,
    get_rfp_snapshot_details,
    update_rfp,
    update_rfp_status,
    reassign_rfp_owner,
    update_rfp_question_answers,
    add_rfp_team_member,
    update_rfp_team_members,
    remove_rfp_team_member,
]


def create_agent() -> Agent:
    """Create and return the meeting broker agent."""
    config = get_config()
    agent = Agent(
        AzureOpenAIResponsesClient(
            project_endpoint=config.azure_ai_project_endpoint,
            deployment_name=config.gpt5_mini_deployment,
            credential=DefaultAzureCredential(),
        ),
        instructions=MEETING_BROKER_INSTRUCTIONS,
        name="MeetingBrokerAgent",
        tools=_RFP_TOOLS,
    )
    logger.info("Meeting broker agent created with %d RFP tools", len(_RFP_TOOLS))
    return agent
