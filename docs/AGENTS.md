# Agents


## 1. Intent Agent


Purpose:

Convert human language into structured intent.


Input:

User message


Output:

Intent object



---

## 2. Memory Agent


Purpose:

Personalize decisions.


Input:

User history


Output:

Preference model



---

## 3. Retrieval Agent


Purpose:

Find possible options.


Input:

Intent


Output:

Candidates



---

## 4. World Model Agent


Purpose:

Represent reality.


Checks:

- location
- time
- cost
- availability



---

## 5. Planner Agent


Purpose:

Generate possible solutions.


Important:

Planner creates options.

Planner does NOT select final answer.



---

## 6. Optimizer Agent


Purpose:

Choose best solution.


Uses:

Constraint optimization


Example:

maximize:

user satisfaction


subject:

budget
time
availability



---

## 7. Critic Agent


Purpose:

Attack the plan.


Questions:

"What can fail?"

"Is this realistic?"

"Does this satisfy user?"