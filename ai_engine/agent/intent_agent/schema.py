from pydantic import BaseModel, Field
from typing import List, Optional

class Preferences(BaseModel):
    """
    Represents user preferences for the AI engine.

    Attributes:
        travel_style (Optional[str]): The user's preferred style of travel (e.g., budget, luxury, adventure).
        priorities (Optional[List[str]]): A list of priorities that the user wants to focus on during planning (e.g., sightseeing, relaxation, cultural experiences).
        avoid (Optional[List[str]]): A list of things the user wants to avoid during planning (e.g., certain activities, locations, or experiences).
    """
    travel_style: Optional[str] = Field(None, description="The user's preferred style of travel (e.g., budget, luxury, adventure).")
    priorities: List[str] = Field(default_factory=list)
    avoid: Optional[List[str]] = Field(None, description="A list of things the user wants to avoid during planning (e.g., certain activities, locations, or experiences).")


class Constraints(BaseModel):
    """
    Represents constraints for the AI engine.

    Attributes:
        budget (Optional[float]): The maximum budget for the plan.
        destination (Optional[str]): The desired destination for the plan.
        duration_days (Optional[int]): The desired duration of the plan in days.
    """
    source: Optional[str] = Field(
        default=None,
        description="Starting location if mentioned."
    )
    budget: Optional[float] = Field(None, description="The maximum budget for the plan.")
    destination: Optional[str] = Field(
    None,
    description="The desired destination for the plan."
)
    duration_days: Optional[int] = Field(None, description="The desired duration of the plan in days.")
    start_date: Optional[str] = Field(
        default=None
    )

class Traveler(BaseModel):
    """
    Represents a traveler for the AI engine.

    Attributes:
        type (str): The type of traveler (e.g., solo, couple, family).
        count (int): The number of travelers of this type.
    """
    type: Optional[str] = None
    count: Optional[int] = None


class Intent(BaseModel):

    """         
    Represents the intent of the user for the AI engine.
        
        Attributes:
            goal_type (str): The type of goal the user wants to achieve (e.g., travel, event planning, personal development).
            traveler (Traveler): The traveler information.
            preferences (Preferences): The user's preferences for the plan.
            constraints (Constraints): Any constraints or limitations that need to be considered during planning.
            missing_information (List[str]): A list of any missing information that needs to be provided by the user for effective planning.
            
            """

    goal_type: str = Field(..., description="The type of goal the user wants to achieve (e.g., travel, event planning, personal development).")
    traveler: Traveler
    preferences: Preferences
    constraints: Constraints
    missing_information: List[str] = []

