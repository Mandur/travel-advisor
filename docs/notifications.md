---
title: Agent Notifications
description: How to receive and handle proactive M365 notifications and lifecycle events in the hack-trial multi-agent system using microsoft-agents-a365-notifications
author: hack-trial
ms.date: 2026-03-05
ms.topic: how-to
keywords:
  - notifications
  - microsoft-agents-a365-notifications
  - m365
  - outlook
  - teams
  - lifecycle events
estimated_reading_time: 8
---

## Overview

The `microsoft-agents-a365-notifications` package, part of the [Microsoft Agent 365 SDK](https://github.com/microsoft/Agent365-python), lets your agents receive **inbound push notifications** from Microsoft 365 applications: Outlook email, Word comments, Excel comments, PowerPoint comments, and agent lifecycle events.

These notifications arrive at the same `/api/messages` endpoint already wired in [`advisor/shared/src/shared/teams_adapter.py`](../advisor/shared/src/shared/teams_adapter.py). The `AgentNotification` class wraps your existing `AgentApplication` to add decorator-based routing on top.

> [!IMPORTANT]
> This package is distinct from `microsoft-agents-hosting-core` and `microsoft-agents-hosting-fastapi`, which handle the Teams/Bot Service channel. The notifications package adds M365 app channels on top of the same transport.

## Installation

Add the package to the shared library's dependencies in [`advisor/shared/pyproject.toml`](../advisor/shared/pyproject.toml):

```toml
dependencies = [
    ...
    "microsoft-agents-a365-notifications>=0.1.0",
]
```

Then sync the workspace:

```bash
uv sync --all-packages
```

## Concepts

### How notifications reach the agent

Every M365 notification is delivered as a Bot Framework `Activity` POSTed to `/api/messages`. The activity carries a `channel_id` field with two parts:

| Field         | Value                              |
|---------------|------------------------------------|
| `channel`     | Always `"agents"` for M365 apps    |
| `sub_channel` | The originating app (`"email"`, `"word"`, `"excel"`, `"powerpoint"`) |

Lifecycle events are delivered with `channel = "agents"` and `activity.name = "agentNotification"`.

### AgentNotification

`AgentNotification` wraps your `AgentApplication` instance and registers route selectors for each handler you decorate. When an activity arrives, the routing logic checks the channel, subchannel, and event type to find the matching handler.

## Setup

Extend `create_teams_router` in [`advisor/shared/src/shared/teams_adapter.py`](../advisor/shared/src/shared/teams_adapter.py) to attach an `AgentNotification` instance to the same `AgentApplication`:

```python
from microsoft_agents_a365.notifications import AgentNotification, AgentSubChannel

# After creating agent_app = AgentApplication(...)
notifications = AgentNotification(agent_app)
```

Pass `known_subchannels` if you register custom subchannels beyond the built-in M365 set:

```python
notifications = AgentNotification(
    agent_app,
    known_subchannels=list(AgentSubChannel) + ["my-custom-subchannel"],
)
```

## Handling M365 notifications

### Outlook email

```python
from microsoft_agents_a365.notifications import AgentNotification, EmailResponse

@notifications.on_email()
async def handle_email(context, state, notification):
    email = notification.email  # EmailReference | None
    if email:
        response = EmailResponse.create_email_response_activity(
            "<p>Thank you for your email. I will respond shortly.</p>"
        )
        await context.send_activity(response)
```

The `notification.email` property returns an `EmailReference` model with fields such as `id`, `subject`, `sender`, and `body_preview`.

### Word, Excel, and PowerPoint comments

```python
@notifications.on_word()
async def handle_word_comment(context, state, notification):
    comment = notification.wpx_comment  # WpxComment | None
    if comment:
        print(f"Word comment {comment.comment_id}: {comment.text}")

@notifications.on_excel()
async def handle_excel_comment(context, state, notification):
    comment = notification.wpx_comment
    if comment:
        await context.send_activity(f"Received Excel comment: {comment.comment_id}")

@notifications.on_powerpoint()
async def handle_ppt_comment(context, state, notification):
    comment = notification.wpx_comment
    if comment:
        await context.send_activity(f"Received PowerPoint comment: {comment.comment_id}")
```

## Handling lifecycle events

Lifecycle events signal changes to agentic user identities, such as provisioning or deprovisioning.

### Individual event handlers

```python
@notifications.on_user_created()
async def handle_user_created(context, state, notification):
    print("New agentic user identity created")

@notifications.on_user_deleted()
async def handle_user_deleted(context, state, notification):
    print("Agentic user identity deleted")

@notifications.on_user_workload_onboarding()
async def handle_onboarding_update(context, state, notification):
    print("User workload onboarding status updated")
```

### Catch-all lifecycle handler

```python
@notifications.on_lifecycle()
async def handle_any_lifecycle(context, state, notification):
    print(f"Lifecycle event type: {notification.notification_type}")
```

## Generic channel routing

Use `on_agent_notification()` directly when you need explicit control over which channel and subchannel to match, or when routing to a channel that has no convenience decorator.

```python
from microsoft_agents.activity import ChannelId
from microsoft_agents_a365.notifications import AgentSubChannel

# Explicit subchannel by string
@notifications.on_agent_notification(
    ChannelId(channel="agents", sub_channel="email")
)
async def handle_email_explicit(context, state, notification):
    ...

# Explicit subchannel using the enum
@notifications.on_agent_notification(
    ChannelId(channel="agents", sub_channel=AgentSubChannel.WORD)
)
async def handle_word_explicit(context, state, notification):
    ...

# Wildcard: match all subchannels under "agents"
@notifications.on_agent_notification(
    ChannelId(channel="agents", sub_channel="*")
)
async def catch_all(context, state, notification):
    print(f"Received on channel={notification.channel} sub={notification.sub_channel}")
```

The convenience methods (`on_email`, `on_word`, etc.) call `on_agent_notification()` with the corresponding `ChannelId` internally.

## Custom channels

You can route activities from your own backend services through the same mechanism. Register the custom subchannel when constructing `AgentNotification` and send a Bot Framework `Activity` with the matching `channel_id` to `/api/messages`:

```python
# Agent side
notifications = AgentNotification(
    agent_app,
    known_subchannels=list(AgentSubChannel) + ["booking-confirmed"],
)

@notifications.on_agent_notification(
    ChannelId(channel="internal", sub_channel="booking-confirmed")
)
async def handle_booking(context, state, notification):
    payload = notification.activity.value  # dict, parse yourself
    booking_id = payload.get("booking_id")
```

There is no typed model for custom subchannels. Parse `notification.activity.value` directly as a dictionary.

> [!WARNING]
> Custom channels bypass M365 delivery infrastructure. Your backend must POST a valid Bot Framework `Activity` directly to the agent's `/api/messages` endpoint. Ensure you handle authentication appropriately.

## Data models

| Model                       | Description                                        |
|-----------------------------|----------------------------------------------------|
| `AgentNotificationActivity` | Wrapper around the raw `Activity` with typed props |
| `EmailReference`            | Outlook email metadata (id, subject, sender, body) |
| `EmailResponse`             | Helper to construct an email reply activity        |
| `WpxComment`                | Word/Excel/PowerPoint comment payload              |
| `AgentSubChannel`           | Enum of known M365 subchannels                     |
| `AgentLifecycleEvent`       | Enum of known lifecycle event types                |
| `NotificationTypes`         | Constants for `activity.name` values               |

Import all models directly from the top-level package:

```python
from microsoft_agents_a365.notifications import (
    AgentNotification,
    AgentNotificationActivity,
    EmailReference,
    EmailResponse,
    WpxComment,
    AgentSubChannel,
    AgentLifecycleEvent,
    NotificationTypes,
)
```

## Reference

| Resource                                                                                                                                              | Description                                              |
|-------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| [microsoft/Agent365-python](https://github.com/microsoft/Agent365-python)                                                                            | Source repository for the Agent 365 Python SDK           |
| [notifications library source](https://github.com/microsoft/Agent365-python/tree/main/libraries/microsoft-agents-a365-notifications)                 | Source code for `microsoft-agents-a365-notifications`    |
| [Microsoft Learn: Notifications](https://learn.microsoft.com/microsoft-agent-365/developer/notification?tabs=python)                                 | Official usage documentation on Microsoft Learn          |
| [Microsoft Learn: Agent 365 Developer docs](https://learn.microsoft.com/microsoft-agent-365/developer/)                                              | Full Agent 365 developer reference                       |
| [advisor/shared/src/shared/teams_adapter.py](../advisor/shared/src/shared/teams_adapter.py)                                                          | Teams adapter where `AgentApplication` is constructed    |
| [advisor/shared/pyproject.toml](../advisor/shared/pyproject.toml)                                                                                    | Shared library dependencies                              |
| [advisor/agents/advisor_agent/src/advisor_agent/main.py](../advisor/agents/advisor_agent/src/advisor_agent/main.py)                                  | Routing agent FastAPI entry point                        |
