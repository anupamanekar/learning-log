---
title: "Non-Deterministic Agentic Workflows: Evals & Golden Data Sets"
slug: "non-deterministic-agentic-workflows-evals-golden-data-set"
description: "How to benchmark non-deterministic developer agent workflows by mining historical GitHub commits to build high-fidelity golden evaluation datasets."
date: "2026-08-30"
status: "Published"
tags: ["agentic-workflows", "evals", "golden-datasets", "testing", "ai-code-generation"]
image: "/images/golden-dataset-workflow.png"
---


## Introduction

In today’s software development landscape, code generation through agents and automated workflows has become increasingly prevalent. However, verifying the correctness of generated code can be a daunting task. 

This is where **golden data sets** come in: pre-generated, verified datasets that serve as a benchmark for testing and validation. In this post, we explore how to successfully construct an evaluation harness and golden data set for developer workflows by systematically leveraging historical GitHub commits.

---

## The Problem: Verifying Code Generation

Automated code generation through agents and workflows has commoditized many parts of software development, enabling faster delivery and iterative experimentation. 

However, with great power comes great responsibility—ensuring that generated code is correct, adheres to architectural invariants, and meets required standards remains a significant challenge. Without rigorous evaluation, subtle regressions and hallucinations slip through into production codebases.

---

## The Challenge: Non-Deterministic Workflows

One key difference between traditional product development and developer workflows is the level of determinism involved:

- **Traditional Product Rules**: Business logic typically has explicit constraints dictating how data should be transformed. These rules can be tested against static sample inputs with exact string or value assertions.
- **Complex Agentic Workflows**: Multi-step developer workflows are inherently non-deterministic. Execution depends on non-linear prompt interpretations, external dependencies, repository context, and dynamic environmental state. Predicting exact character-by-character output for any given prompt is impractical.

Because agents can achieve a valid goal through multiple distinct syntax trees, traditional unit testing assertions often fail or provide false negatives.

---

## The Solution: Leveraging Past Commit History

Golden data sets serve as an authoritative reference benchmark for testing and validation. By comparing the output of automated agent workflows against these curated benchmarks, teams can evaluate whether generated solutions preserve semantics, pass linting, and solve real issues.

However, hand-crafting synthetic evaluation benchmarks is time-consuming, expensive, and quickly drifts from real-world codebase challenges.

A practical and scalable approach is **mining historical GitHub commits**. Past pull requests and commits contain:
1. The exact issue description or review comments.
2. The initial codebase state before the change.
3. The human-approved, battle-tested resolution diff.

By extracting these past states, we can run agentic workflows against historical scenarios and evaluate their outputs against proven historical ground truth.

---

## Workflow Architecture: Ingestion Pipeline & Execution

The diagram below illustrates the end-to-end architecture: from raw commit mining and data processing into versioned golden datasets, to driving automated developer workflows with semantic reviews and regression testing.

![Golden Data Set Workflow Pipeline](/images/golden-dataset-workflow.png)

### 1. Data Preparation & Ingestion Pipeline
- **Extract File Changes & Comments**: Analyze commit history, PR descriptions, and code reviews using GitHub APIs.
- **Extracted Data Processing**: Parse, normalize, and enrich the diffs and surrounding context into standard test fixtures.
- **Golden Datasets (Versioned Data Store)**: Store curated, cleaned benchmarks organized by domain with full historical context.

### 2. Developer Workflow (From Golden Datasets)
- **Load Golden Datasets**: Pull test cases and historical repository state from the versioned store.
- **Semantic Review**: Combine AI-assisted evaluation and human oversight to judge semantic correctness over strict syntactic matching.
- **Regression Testing**: Execute automated and AI-generated test suites against the agent's proposed changes.
- **Critique & Best Practices**: Verify code quality, formatting, security, and performance against team guidelines.
- **Confident Merge**: Ship generated enhancements with high confidence.

---

## Key Benefits

By building golden datasets directly from historical repository activity, teams achieve:

- **Improved Code Quality**: Consistent, multi-dimensional test cases ensure agent-generated code satisfies both functional and architectural requirements.
- **Reduced Benchmark Creation Time**: Rather than writing artificial scenarios from scratch, replaying real commits automates test generation at scale.
- **Increased Confidence & Alignment**: Grounding evals in production commit history ensures that automated agent workflows perform well on actual team problems.

---

I hope this write-up provides a practical blueprint for designing evaluation harnesses and golden datasets for your agentic development workflows.
