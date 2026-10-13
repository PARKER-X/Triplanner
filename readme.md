# Triplanner ✈️
### From AI-Generated Itineraries to Constraint-Aware Travel Planning

**Triplanner is an AI-powered trip-planning project exploring how Large Language Models (LLMs), information retrieval, ranking, and Operations Research can work together to generate realistic and personalized travel itineraries.**

The goal is simple: move beyond itineraries that merely *look good* toward plans that account for real-world constraints.

## 🎯 The Problem

LLMs can understand natural-language requests and suggest interesting destinations, restaurants, and activities. However, generating a convincing itinerary does not guarantee a feasible one.

A generated plan may:

- Schedule attractions outside their opening hours.
- Include unrealistic travel times between locations.
- Pack too many activities into a single day.
- Ignore budget, duration, or user preferences.
- Repeat activities across multiple days.
- Recommend places without sufficiently reliable or current information.

Travel planning is therefore not just a text-generation problem. It is also a **retrieval, scheduling, ranking, and constrained optimization problem.**

## 💡 The Core Idea

Triplanner explores a hybrid approach in which each component solves a different part of the problem.

| Component | Responsibility |
|---|---|
| LLM | Understand user intent and interpret preferences |
| Retrieval | Find relevant destinations and real-world information |
| Ranking | Prioritize activities based on user preferences |
| Optimization | Construct itineraries subject to logistical constraints |
| Validation | Check feasibility and identify inconsistencies |

The central principle is to combine the flexibility of language models with the rigor of mathematical optimization.

## 🏗️ Proposed Architecture

```text
              User Request
                   |
                   v
              Planner Agent
                   |
                   v
             Intent Extraction
                   |
                   v
          Retrieval of Activities
                   |
                   v
           Activity Ranking
                   |
                   v
         Constraint Optimization
                   |
                   v
               Validation
                   |
                   v
          Final Travel Itinerary
```

### 1. Intent Understanding

Convert a natural-language request into structured planning requirements.

For example:

> Plan a three-day trip to New York with hidden gems, museums, good food, and minimal travel time.

The system should extract the destination, duration, preferences, budget, and other available constraints.

### 2. Retrieval and Grounding

Retrieve candidate activities and relevant information, such as:

- Locations and geographical coordinates
- Opening hours and availability
- Estimated travel times
- Activity duration and cost
- Descriptions and preference-related attributes

Time-sensitive information should be verified against reliable sources wherever possible.

### 3. Activity Ranking

Rank candidate activities according to their relevance to the user's preferences.

For example, someone interested in quiet, lesser-known places may prefer a small local museum over a crowded tourist attraction.

### 4. Constraint Optimization

Treat itinerary construction as a decision problem.

Possible constraints include:

- Visiting only attractions that fit the available schedule
- Respecting opening hours
- Accounting for travel time between activities
- Staying within the trip budget
- Avoiding duplicate activities
- Limiting the number of activities per day

A simplified objective could balance preference satisfaction and travel efficiency:

\[
\max \left(
\alpha \cdot \text{Preference Score}
-\beta \cdot \text{Travel Cost}
\right)
\]

Here, \(\alpha\) and \(\beta\) control the relative importance of preference satisfaction and travel efficiency.

This is a conceptual objective, not a claim that the current code already implements this exact formulation.

### 5. Validation

Before presenting an itinerary, check whether it respects the available constraints.

If an activity is unavailable or the schedule is infeasible, the system should identify the problem and consider alternatives rather than silently producing an unreliable plan.

## 🔬 Research Inspiration

Triplanner is inspired in part by Google's research blog:

**[Optimizing LLM-based Trip Planning — Google Research](https://research.google/blog/optimizing-llm-based-trip-planning/)**

The work illustrates how LLM-generated plans can be combined with real-world information and optimization methods to improve itinerary feasibility.

I am using this research direction as a learning and experimentation opportunity to explore the intersection of AI and Operations Research.

Triplanner is an independent project, not an official Google implementation.

## 🛠️ Technology and Methods

The project explores the following areas:

- Large Language Models and agent architectures
- Information retrieval and data grounding
- Ranking and preference modeling
- Operations Research and constraint optimization
- Automated validation and evaluation
- API and user-interface development

The specific tools and algorithms will be documented as they are implemented and evaluated.


## 📊 Evaluation Goals

The aim is to evaluate itinerary quality beyond how convincing the generated text sounds.

Potential evaluation metrics include:

- **Feasibility:** Does the itinerary satisfy the encoded constraints?
- **Travel efficiency:** How much time is spent travelling?
- **Preference alignment:** Does the plan reflect the user's priorities?
- **Budget compliance:** Does the plan remain within the specified budget?
- **Duplicate activities:** Are activities repeated unnecessarily?
- **Planning latency:** How long does the system take to generate a plan?

Where possible, the project will compare an LLM-only baseline with retrieval-enhanced and optimization-enhanced approaches.

## 🌱 Current Status

**Early-stage project — architecture and experimentation.**

The current focus is on understanding the problem, studying relevant research, and building the system incrementally. The proposed architecture and roadmap describe the intended direction; individual capabilities will be marked complete as they are implemented and tested.

## 📚 Learning Goals

Through Triplanner, I want to explore a broader question:

**How can we combine the reasoning and language capabilities of LLMs with mathematical methods that make decisions under real-world constraints?**

Although travel planning is the initial application, the underlying ideas are relevant to many other domains, including vehicle routing, workforce scheduling, inventory management, and resource allocation.

## 🔗 Links

- **Repository:** https://github.com/PARKER-X/Triplanner
- **Research inspiration:** https://research.google/blog/optimizing-llm-based-trip-planning/

---

*Built as a learning and experimentation project at the intersection of Artificial Intelligence and Operations Research.*
