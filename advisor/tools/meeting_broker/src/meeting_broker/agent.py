"""Meeting broker -- wraps the RFP API as async agent tools."""
# Ver 1.1
from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.tools import tool

from shared.config import get_config
from shared.utils import setup_logging
from shared.tools.http_client import ApiClient
from meeting_broker.rfp_models import (
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

logger = setup_logging("meeting-broker")

_DEFAULT_PAGE_LIMIT = 100


@lru_cache(maxsize=1)
def _client() -> ApiClient:
    config = get_config()
    return ApiClient(
        base_url=config.rfp_api_base_url,
        bearer_token=config.bearer_token,
        timeout=config.rfp_api_timeout,
    )


# -- Search & retrieve --------------------------------------------------------


async def _search_rfps_impl(
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
) -> dict[str, Any]:
    effective_limit = _DEFAULT_PAGE_LIMIT if limit is None else limit

    raw = await _client().get(
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
            "limit": effective_limit,
            "sortBy": sort_by,
            "rfpMilestone": rfp_milestone,
            "nextStepName": next_step_name,
            "nextStepDueDate": next_step_due_date,
            "continuationToken": continuation_token,
            "isNextStepOverdue": is_next_step_overdue,
            "isExport": is_export,
        },
    )
    return SearchRfpResponse.model_validate(raw).model_dump()


@tool
async def search_rfps(
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
) -> dict[str, Any]:
    """Search and retrieve a list of RFPs matching the supplied filters.

    All parameters are optional -- omit any you do not need.

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
        internal_id: Internal RFP identifier.
        location_name: Name of the receiving location.
        limit: Maximum number of results to return (defaults to 100).
        sort_by: Column to sort results by.
        rfp_milestone: Milestone type name (e.g. "Published", "Viewed").
        next_step_name: Partial name of the next step action.
        next_step_due_date: Due date for the next step in YYYYMMDD format.
        continuation_token: Token for the next page of results.
        is_next_step_overdue: Filter to only overdue next steps when True.
        is_export: Set to True when exporting results to a file.

    Returns:
        Dict with a list of RFP summaries and total count.
    """
    return await _search_rfps_impl(
        meeting_name=meeting_name,
        account_name=account_name,
        status=status,
        arrival_date=arrival_date,
        received_date=received_date,
        total_budget=total_budget,
        rate=rate,
        proposal_sent_date=proposal_sent_date,
        external_rfp_id=external_rfp_id,
        internal_id=internal_id,
        location_name=location_name,
        limit=limit,
        sort_by=sort_by,
        rfp_milestone=rfp_milestone,
        next_step_name=next_step_name,
        next_step_due_date=next_step_due_date,
        continuation_token=continuation_token,
        is_next_step_overdue=is_next_step_overdue,
        is_export=is_export,
    )


@tool
async def list_rfps(
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
) -> dict[str, Any]:
    """List RFPs matching the supplied filters.

    Alias of search_rfps with identical parameters and behavior.
    """
    return await _search_rfps_impl(
        meeting_name=meeting_name,
        account_name=account_name,
        status=status,
        arrival_date=arrival_date,
        received_date=received_date,
        total_budget=total_budget,
        rate=rate,
        proposal_sent_date=proposal_sent_date,
        external_rfp_id=external_rfp_id,
        internal_id=internal_id,
        location_name=location_name,
        limit=limit,
        sort_by=sort_by,
        rfp_milestone=rfp_milestone,
        next_step_name=next_step_name,
        next_step_due_date=next_step_due_date,
        continuation_token=continuation_token,
        is_next_step_overdue=is_next_step_overdue,
        is_export=is_export,
    )


@tool
async def get_rfp(rfp_id: str, children: str | None = None) -> dict[str, Any]:
    """Retrieve full details for a single RFP by its GUID.

    Args:
        rfp_id: UUID of the RFP to retrieve.
        children: Comma-separated list of child nodes to include (e.g. "questions,team").

    Returns:
        Dict with the full RFP detail object.
    """
    raw = await _client().get(f"/rfps/{rfp_id}", params={"children": children})
    return GetRfpResponse.model_validate(raw).model_dump()


@tool
async def get_rfp_status_counts(
    start_date: str | None = None,
    end_date: str | None = None,
    statuses: str | None = None,
    location_ids: str | None = None,
) -> dict[str, Any]:
    """Retrieve the count of RFPs grouped by status for a date range.

    Args:
        start_date: Start of the date range in YYYYMMDD format.
        end_date: End of the date range in YYYYMMDD format.
        statuses: Comma-delimited list of status names to filter by.
        location_ids: Comma-delimited list of location IDs to restrict counts to.

    Returns:
        Dict with per-status counts.
    """
    raw = await _client().get(
        "/rfps/status-counts",
        params={
            "startDate": start_date,
            "endDate": end_date,
            "statuses": statuses,
            "locationIds": location_ids,
        },
    )
    return StatusCountsResponse.model_validate(raw).model_dump()


@tool
async def get_rfp_status_revenues(
    start_date: str | None = None,
    end_date: str | None = None,
    statuses: str | None = None,
    is_actual: bool | None = None,
    location_ids: str | None = None,
) -> dict[str, Any]:
    """Retrieve RFP revenue figures grouped by status for a date range.

    Args:
        start_date: Start of the date range in YYYYMMDD format.
        end_date: End of the date range in YYYYMMDD format.
        statuses: Comma-delimited list of RFP status names to include.
        is_actual: True for actual revenue totals; False (default) for forecast.
        location_ids: Comma-delimited list of location IDs to filter by.

    Returns:
        Dict with revenue per status.
    """
    raw = await _client().get(
        "/rfps/status-revenues",
        params={
            "startDate": start_date,
            "endDate": end_date,
            "statuses": statuses,
            "isActual": is_actual,
            "locationIds": location_ids,
        },
    )
    return StatusRevenueResponse.model_validate(raw).model_dump()


@tool
async def get_rfp_questions(rfp_id: str) -> dict[str, Any]:
    """Retrieve the questions and answers associated with an RFP.

    Args:
        rfp_id: UUID of the RFP.

    Returns:
        Dict with the list of questions and their answers.
    """
    raw = await _client().get(f"/rfps/{rfp_id}/questions")
    return QuestionsResponse.model_validate(raw).model_dump()


@tool
async def get_rfp_additional_information(rfp_id: str) -> dict[str, Any]:
    """Retrieve the additional information fields attached to an RFP.

    Args:
        rfp_id: UUID of the RFP.

    Returns:
        Dict with extra key/value fields.
    """
    raw = await _client().get(f"/rfps/{rfp_id}/additional-information")
    return AdditionalInfoResponse.model_validate(raw).model_dump()


@tool
async def get_rfp_team(
    rfp_id: str,
    limit: int | None = None,
    continuation_token: str | None = None,
) -> dict[str, Any]:
    """Retrieve the team members assigned to an RFP.

    Args:
        rfp_id: UUID of the RFP.
        limit: Maximum number of team members to return (defaults to 100).
        continuation_token: Token for the next page of results.

    Returns:
        Dict with team members and total count.
    """
    effective_limit = _DEFAULT_PAGE_LIMIT if limit is None else limit

    raw = await _client().get(
        f"/rfps/{rfp_id}/team",
        params={"limit": effective_limit, "continuationToken": continuation_token},
    )
    return TeamResponse.model_validate(raw).model_dump()


@tool
async def get_rfp_proposal_providers(rfp_id: str, channel_id: int | None = None) -> dict[str, Any]:
    """Retrieve the list of proposal providers associated with an RFP.

    Args:
        rfp_id: UUID of the RFP.
        channel_id: Optional channel integer ID.

    Returns:
        Dict with the provider list.
    """
    raw = await _client().get(
        f"/rfps/{rfp_id}/proposal-providers",
        params={"channelId": channel_id},
    )
    return ProposalProvidersResponse.model_validate(raw).model_dump()


@tool
async def get_rfp_snapshots(rfp_id: str) -> dict[str, Any]:
    """Retrieve the list of available snapshots (historical versions) for an RFP.

    Args:
        rfp_id: UUID of the RFP.

    Returns:
        Dict with snapshot IDs and version labels.
    """
    raw = await _client().get(f"/rfps/{rfp_id}/snapshots")
    return SnapshotsResponse.model_validate(raw).model_dump()


@tool
async def get_rfp_snapshot_details(rfp_id: str, snapshot_id: int | None = None) -> dict[str, Any]:
    """Compare an RFP snapshot against the current version field-by-field.

    Args:
        rfp_id: UUID of the RFP.
        snapshot_id: Integer ID of the snapshot to compare.

    Returns:
        Dict with sections of changed fields.
    """
    raw = await _client().get(
        f"/rfps/{rfp_id}/compare-side-by-side",
        params={"snapshotId": snapshot_id},
    )
    return SnapshotDetailsResponse.model_validate(raw).model_dump()


# -- Write operations ---------------------------------------------------------


@tool
async def update_rfp(rfp_id: str, rfp_details: dict[str, Any]) -> dict[str, Any]:
    """Update the content of an existing RFP.

    Provide only the fields you want to change inside rfp_details.

    Args:
        rfp_id: UUID of the RFP to update.
        rfp_details: Partial or full RfpDetails object to apply.

    Returns:
        Dict with success status.
    """
    await _client().put(f"/rfps/{rfp_id}", json={"data": rfp_details})
    return NoContentResponse().model_dump()


@tool
async def update_rfp_status(
    rfp_id: str,
    status: str,
    comment: str | None = None,
    start_date: str | None = None,
    reason_id: str | None = None,
) -> dict[str, Any]:
    """Change the status of an RFP and optionally record business data.

    Valid status values: New, Declined, Awarded, TurnedDown, Cancelled,
    Responded, Viewed, Published.

    Args:
        rfp_id: UUID of the RFP.
        status: Target RFP status string.
        comment: Optional comment to record with the status change.
        start_date: Optional business data start date (ISO-8601 string).
        reason_id: Optional lost-business reason ID.

    Returns:
        Dict with a reference to the updated RFP.
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
    raw = await _client().put(f"/rfps/{rfp_id}/status", json=body)
    return PutResponse.model_validate(raw).model_dump()


@tool
async def reassign_rfp_owner(rfp_id: str, new_owner: dict[str, Any]) -> dict[str, Any]:
    """Reassign the owner of an RFP.

    Args:
        rfp_id: UUID of the RFP.
        new_owner: PersonSummary object identifying the new owner (must include "id").

    Returns:
        Dict with a reference to the updated RFP.
    """
    raw = await _client().put(f"/rfps/{rfp_id}/owner", json={"data": {"owner": new_owner}})
    return PutResponse.model_validate(raw).model_dump()


@tool
async def update_rfp_question_answers(rfp_id: str, questions: list[dict[str, Any]]) -> dict[str, Any]:
    """Update the answers to one or more questions on an RFP.

    Args:
        rfp_id: UUID of the RFP.
        questions: List of question objects with updated answers.

    Returns:
        Dict with the updated question list.
    """
    raw = await _client().put(
        f"/rfps/{rfp_id}/questions/answers",
        json={"data": {"questions": questions}},
    )
    return UpdateQuestionsResponse.model_validate(raw).model_dump()


@tool
async def add_rfp_team_member(
    rfp_id: str,
    user_id: str,
    role_id: str | None = None,
) -> dict[str, Any]:
    """Add a member to the RFP team.

    Args:
        rfp_id: UUID of the RFP.
        user_id: UUID of the user to add.
        role_id: Optional UUID of the role to assign to the new member.

    Returns:
        Dict with the new team member ID.
    """
    member: dict[str, Any] = {"person": {"id": user_id}}
    if role_id is not None:
        member["role"] = {"id": role_id}
    raw = await _client().post(f"/rfps/{rfp_id}/team/members", json={"data": member})
    return TeamMemberResponse.model_validate(raw).model_dump()


@tool
async def update_rfp_team_members(rfp_id: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    """Update the team members of an RFP in bulk.

    Args:
        rfp_id: UUID of the RFP.
        members: List of TeamMember objects with updated values.

    Returns:
        Dict with success status.
    """
    await _client().put(f"/rfps/{rfp_id}/team/members", json={"data": members})
    return NoContentResponse().model_dump()


@tool
async def remove_rfp_team_member(rfp_id: str, user_id: str) -> dict[str, Any]:
    """Remove a member from the RFP team.

    Args:
        rfp_id: UUID of the RFP.
        user_id: UUID of the team member to remove.

    Returns:
        Dict with success status.
    """
    await _client().delete(f"/rfps/{rfp_id}/team/members/{user_id}")
    return NoContentResponse().model_dump()


# -- Tool list for agents -----------------------------------------------------

_RFP_TOOLS = [
    search_rfps,
    list_rfps,
    get_rfp,
    get_rfp_additional_information,
    update_rfp,
    update_rfp_status,
]
