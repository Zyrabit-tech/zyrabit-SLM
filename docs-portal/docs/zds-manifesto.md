---
sidebar_position: 1
title: 'Design System Manifesto'
description: 'Visual design principles and identity guidelines for the Zyrabit Design System'
---

# Zyrabit Documentation Standard (ZDS)

This document defines the golden rules for all Zyrabit infrastructure documentation. We follow the design patterns of **Stripe** (interactivity), **Apple** (aesthetics), and **OpenAI** (AI-Native clarity).

## 1. Page Structure
Every document must follow this order:
1. **Technical Summary**: A hidden block or brief summary for LLMs/Agents.
2. **Overview**: The "Why" of the functionality.
3. **Quick Start**: The shortest path to success (3 steps maximum).
4. **Deep Dive**: Technical details, diagrams, and references.
5. **Troubleshooting**: Common errors and how to solve them.

## 2. Visual Components
We use GitHub alerts to emphasize information:
- `> [!NOTE]`: Background information or architecture.
- `> [!TIP]`: Productivity shortcuts or best practices.
- `> [!IMPORTANT]`: Critical requirements for data sovereignty.
- `> [!WARNING]`: Actions that could compromise privacy or performance.

## 3. Writing Style
- **Voice**: Active ("Configure the bot" instead of "The bot must be configured").
- **Tone**: Architectural and Confident.
- **Clarity**: Avoid unnecessary adjectives. If something is "fast", prove it with a benchmark, don't just say it.

## 4. AI-Native Ready
Each page must be processable by the **Model Context Protocol (MCP)**. This means using clear headings and metadata in markdown format.
