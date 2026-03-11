# 🧭 Orchestrator Agent — Design Decision Document

Workstream A — Hackathon Prototype

## 1. Purpose

- This document captures the design principles, goals, requirements, constraints, and architectural considerations for the Orchestrator Agent being developed as part of Workstream A.
- It is intended as an input to GitHub Copilot for generating code, scaffolding, architectural stubs, and implementation patterns.

## 2. Background and Context

- Amadeus is building a cross-system orchestrator agent as the central routing mechanism between multiple hotel-tech systems, including Meeting Broker and Travel Advisor.
- The hackathon focuses on producing a functional prototype capable of routing, integrating with mocked systems, and establishing patterns usable for future extensible architectures.
- Additional meetings clarified the larger direction, including:
	- Routing across multiple domains
	- A unified entry point
	- Architectural flexibility
	- Alignment with future customer-tenant deployment models
- Workstream A specifically owns the Agentic Router Mechanism, responsible for classification and routing.

## 3. Goals

### 3.1 Primary Goals

- Build a domain routing mechanism able to route across use-case domains such as RFP creation and Hotel Manager workflows.
- Enable execution and evaluation of business scenarios (RFP use case, Hotel Manager use case).
- Create an orchestrator that acts as a single entry point, dispatching user requests to the appropriate backend or agent.
- Integrate Meeting Broker (via mock) and Travel Advisor QA endpoint.
- Deliver a working prototype within the hackathon constraints.

### 3.2 Secondary Goals

- Establish architectural patterns reusable for other Amadeus systems.
- Support future extensibility, including more channels (Teams, Copilot, possibly WeChat/Slack).

## 4. Requirements

### 4.1 Functional Requirements

- **Routing & Classification**
	- Must classify incoming natural-language requests into domains.
	- Must route to the correct system: Meeting Broker, Travel Advisor, or future services.
- **System Integrations**
	- Integrate with mock Meeting Broker using the Mockzilla endpoint.
	- Integrate with Travel Advisor QA GraphQL endpoint, including authentication.
- **User Interaction Handling**
	- Orchestrator must support consumable responses for Teams/Copilot channels.
- **Access Control**
	- Not all users should have access to all services; require authorization filtering.

### 4.2 Non‑Functional Requirements

- Simplicity first for hackathon.
- Modularity to accommodate new use cases and agents over time.
- Scalability considerations for long-term distributed scenarios, but without over-engineering for prototype.

## 5. Architectural Considerations

### 5.1 Core Architecture Choices

- Conversations explored monolithic vs distributed orchestrator models:
	- **Monolithic:** simpler, fewer moving pieces, ideal for hackathon.
	- **Distributed:** more flexible but significantly more complex (token management, scaling, auth).
- Hackathon recommendation: monolithic-first with clear abstractions to allow gradual decomposition.

### 5.2 Agent Reusability & Migration

- Existing agents such as Email-to-RFP may require rewriting using modern frameworks (e.g., Microsoft Agent Framework).
- The orchestrator must support a unified agent contract for future reuse.

### 5.3 Authentication & Authorization

- Considered options:
	- CIAM
	- Ping Federate
	- Middleware layers
- Decision: simplify authentication for the hackathon; implement only minimal role validation.
- Longer-term: full integration with enterprise identity and HWS tokens.

### 5.4 Platform Constraints

Workstream A platform constraints include:
- Memory limits
- Indexing approaches
- Guardrails

## 6. Design Principles

1. **Simplicity First**
	 - Optimize for hackathon speed. Build the minimal orchestrator capable of routing and integrating with mock systems.
2. **Clear Separation of Concerns**
	 - Routing logic must be decoupled from system integrations via adapter interfaces.
3. **Extensible by Design**
	 - Allow new systems, agents, and channels to be added without major redesign.
4. **Unified Contract**
	 - All system connectors should follow the same request/response envelope to support modularity.
5. **Channel-Agnostic Output**
	 - Ensure orchestrator responses can render in Teams, Copilot, and future channels.
6. **Secure by Default**
	 - Even though simplified for hackathon, design must leave room for real-world authentication & authorization.

## 7. Constraints

### 7.1 Hackathon Constraints

- Very limited time and resources (4-5 contributors).
- Mock systems only (no real MB/TA production connectivity).
- Simplified authentication.

### 7.2 Technical Constraints

- Must align with Microsoft technology stack (Azure services, vector store, model router, etc.).
- UI frameworks still undecided (Adaptive Cards, CopilotKit, AG UI).
