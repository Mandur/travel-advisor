---
title: Adaptive Cards with CopilotKit
description: How to generate and render Adaptive Cards UI using CopilotKit generative UI and Microsoft Agent Framework in the hack-trial multi-agent system
author: hack-trial
ms.date: 2026-03-06
ms.topic: how-to
keywords:
  - adaptive-cards
  - copilotkit
  - generative-ui
  - microsoft-agent-framework
  - teams
  - react
estimated_reading_time: 7
---

## Overview

CopilotKit can be used to generate and display Adaptive Cards UI, though it requires understanding the boundary between the two technologies. CopilotKit renders **React components**; Adaptive Cards are **JSON schemas** rendered natively by host applications such as Teams or the Adaptive Cards JS SDK.

The two work together by having the agent produce Adaptive Card JSON as a tool output, and a registered React component render that JSON using the `adaptivecards` SDK inline in the chat. For Teams users, the existing `teams_adapter.py` can emit the same JSON as a bot attachment without any frontend component.

This document covers both integration paths and how they map to this project.

---

## Key Concepts

### CopilotKit Generative UI

CopilotKit (v1.50+) exposes two main hooks for rendering custom UI from agent outputs:

| Hook | Purpose |
|---|---|
| `useComponent` | Register a React component as a named tool the agent can invoke. The agent calls the tool; CopilotKit renders the component with tool arguments as props. |
| `useRenderTool` | Customize how a specific named backend tool call appears in the chat (with `status` and `args` access during and after execution). |
| `useDefaultRenderTool` | Wildcard fallback renderer for any tool without a dedicated `useRenderTool` handler. |

CopilotKit has first-class support for Microsoft Agent Framework. The generative UI hooks work with any agent that speaks the AG-UI protocol, including Python agents built with `agent_framework`.

### Adaptive Cards

Adaptive Cards are platform-agnostic UI snippets authored in JSON. The host application (Teams, Outlook, Bot Framework webchat, Windows) renders the JSON natively using its own SDK, automatically matching the surrounding look and feel.

Version 1.5 of the schema is the maximum supported by Teams bots today. The JSON schema is well-documented and LLMs generate it reliably when prompted with schema constraints.

---

## Integration Approaches

### Approach A: Web App — CopilotKit React Component

Use this approach when the target surface is a React web application fronted by CopilotKit.

The agent defines a tool that returns Adaptive Card JSON. The React frontend registers a `useComponent` that passes the JSON to the `adaptivecards` JS SDK for browser rendering.

**Backend (Python agent tool):**

```python
from agent_framework import tool

@tool
def render_hotel_card(hotel_name: str, city: str, check_in: str,
                       check_out: str, price_per_night: float) -> dict:
    """Render a hotel pricing card in the chat UI."""
    return {
        "cardJson": json.dumps({
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [
                {"type": "TextBlock", "text": hotel_name, "weight": "Bolder", "size": "Large"},
                {"type": "TextBlock", "text": city},
                {"type": "FactSet", "facts": [
                    {"title": "Check-in", "value": check_in},
                    {"title": "Check-out", "value": check_out},
                    {"title": "Rate", "value": f"${price_per_night:.2f}/night"},
                ]},
            ],
            "actions": [
                {"type": "Action.Submit", "title": "Book now", "data": {"hotel": hotel_name}},
            ],
        })
    }
```

**Frontend (React):**

```tsx
import { useComponent } from "@copilotkit/react-core/v2";
import * as AC from "adaptivecards";
import { z } from "zod";

function AdaptiveCardRenderer({ cardJson }: { cardJson: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ac = new AC.AdaptiveCard();
    ac.parse(JSON.parse(cardJson));
    const el = ac.render();
    ref.current.innerHTML = "";
    if (el) ref.current.appendChild(el);
  }, [cardJson]);

  return <div ref={ref} />;
}

function YourMainContent() {
  useComponent({
    name: "render_hotel_card",
    description: "Render a hotel pricing card",
    parameters: z.object({ cardJson: z.string() }),
    render: AdaptiveCardRenderer,
  });

  return <>{/* ... */}</>;
}
```

Install the renderer:

```bash
npm install adaptivecards
```

### Approach B: Teams Channel — Bot Attachment

Use this approach when the target surface is Microsoft Teams via the existing bot integration. No React frontend is required.

The Teams adapter in [`advisor/shared/src/shared/teams_adapter.py`](../advisor/shared/src/shared/teams_adapter.py) already handles the `/api/messages` endpoint. The agent or a tool can include an Adaptive Card as a bot message attachment by returning a payload in the Bot Framework format:

```python
from agent_framework import tool

@tool
def send_hotel_card_to_teams(hotel_name: str, price: float) -> dict:
    """Send a hotel card to the Teams conversation."""
    card_content = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "text": hotel_name, "weight": "Bolder"},
            {"type": "TextBlock", "text": f"${price:.2f} / night"},
        ],
        "actions": [
            {"type": "Action.Submit", "title": "Book", "data": {"hotel": hotel_name}},
        ],
    }
    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card_content,
        }],
    }
```

The Teams adapter routes the activity back to the channel, and Teams renders the card natively.

### Approach C: LLM-Generated Card Schemas

An LLM can generate Adaptive Card JSON dynamically given a prompt that includes schema constraints. This works well for scenarios where the card layout depends on unstructured user intent.

Prompt the model with the schema version (`1.5`), required elements, and any data to embed. The model returns JSON that you validate with the `adaptivecards` SDK before rendering or sending. Because the Adaptive Cards schema is stable and well-documented, GPT-4o and similar models handle card generation reliably without fine-tuning.

Combine this with Approach A or B: the agent tool calls the LLM, validates the resulting JSON, then either returns it as a `cardJson` string for frontend rendering or emits it as a Teams attachment.

---

## Choosing an Approach

| Criterion | Approach A (React) | Approach B (Teams) | Approach C (LLM-generated) |
|---|---|---|---|
| Target surface | Web app | Teams | Either |
| Frontend required | Yes (React + `adaptivecards` npm) | No | No (pairs with A or B) |
| Backend changes | New `@tool` returning `cardJson` | New `@tool` returning attachment payload | Add LLM call inside existing tool |
| Already scaffolded in this project | Partially (agent framework ready) | Yes (`teams_adapter.py`) | Yes (agents already call LLMs) |

For this project, the most practical starting point is Approach B (Teams channel) because the adapter is already in place. Add Approach A when a web frontend is introduced.

---

## Relevant Project Files

| File | Role |
|---|---|
| [`advisor/shared/src/shared/teams_adapter.py`](../advisor/shared/src/shared/teams_adapter.py) | Teams Bot Framework adapter; handles `/api/messages` |
| [`advisor/shared/src/shared/models.py`](../advisor/shared/src/shared/models.py) | Pydantic models for structured agent data (source for card fields) |
| [`advisor/agents/travel_advisor_agent/src/travel_advisor_agent/agent.py`](../advisor/agents/travel_advisor_agent/src/travel_advisor_agent/agent.py) | Travel agent; natural owner of hotel/flight card tools |
| [`advisor/agents/meeting_broker/src/meeting_broker/agent.py`](../advisor/agents/meeting_broker/src/meeting_broker/agent.py) | Meeting agent; natural owner of meeting summary or room booking cards |

---

## References

- [CopilotKit Generative UI — Display Components](https://docs.copilotkit.ai/generative-ui/your-components/display-only)
- [CopilotKit + Microsoft Agent Framework](https://docs.copilotkit.ai/microsoft-agent-framework/)
- [CopilotKit Tool Rendering (Microsoft Agent Framework)](https://docs.copilotkit.ai/microsoft-agent-framework/generative-ui/tool-rendering)
- [Adaptive Cards Overview](https://learn.microsoft.com/en-us/adaptive-cards/)
- [Adaptive Cards Documentation Hub](https://adaptivecards.microsoft.com/)
- [Teams Adaptive Card Reference](https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-reference)
- [`adaptivecards` npm package](https://www.npmjs.com/package/adaptivecards)
