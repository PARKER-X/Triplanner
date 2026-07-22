# Orchestration


## Responsibility

The orchestrator controls:

- workflow
- agent execution order
- retries
- failures


The orchestrator does NOT:

- make plans
- decide answers
- replace agents


---

## Architecture


                User

                 |

              API

                 |

          Orchestrator

                 |

       Planning State Manager


                 |

 ---------------------------------

 |       |       |       |        |

Intent Memory Retrieval Planner Optimizer


                 |

              Evaluator


                 |

              Response


---

## Execution Model


Step 1:

Create PlanningState


Step 2:

Run Intent Agent


Step 3:

Update state


Step 4:

Run retrieval + memory in parallel


Step 5:

Generate candidate plans


Step 6:

Optimize


Step 7:

Critic evaluation


Step 8:

Return final answer

