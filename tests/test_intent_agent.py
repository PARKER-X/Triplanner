from ai_engine.agent.intent_agent.intent_agent import IntentAgent
from ai_engine.core.llm.gemini import GeminiProvider



def run_test(name, user_input):

    print("\n")
    print("=" * 80)
    print(name)
    print("=" * 80)

    llm = GeminiProvider()

    agent = IntentAgent(llm)


    result = agent.run(
        user_input
    )


    print("\nOUTPUT:")
    print(
        result.model_dump_json(
            indent=2
        )
    )


    # Basic checks

    assert result.goal_type is not None

    assert result.constraints is not None

    assert result.preferences is not None

    assert result.traveler is not None



# -------------------------------------
# Test 1: Japan Family Trip
# -------------------------------------

def test_japan_family_trip():

    run_test(
        "Japan Family Trip",

        """
        I want a relaxing 10 day Japan trip
        with my wife and two children.

        Budget is $4000.

        We like nature and culture.

        Avoid crowded places.
        """
    )



# -------------------------------------
# Test 2: Indian Family Trip
# -------------------------------------

def test_kashmir_family_trip():

    run_test(
        "Kashmir Family Trip",

        """
        I want a family vacation to Kashmir.

        We are 5 people.

        Budget is ₹150000.

        Duration is 7 days.

        We want snow, sightseeing
        and comfortable hotels.

        Avoid difficult trekking.
        """
    )



# -------------------------------------
# Test 3: Source Destination
# -------------------------------------

def test_source_destination():

    run_test(
        "Delhi To Japan",

        """
        I want to travel from Delhi
        to Japan.

        It is a 12 day trip.

        Budget is 2 lakh rupees.
        """
    )



# -------------------------------------
# Test 4: Friends Trip India
# -------------------------------------

def test_goa_friends_trip():

    run_test(
        "Goa Friends Trip",

        """
        Me and my 6 friends want
        to visit Goa.

        Budget is 60000 rupees.

        Trip duration is 5 days.

        We like beaches and nightlife.

        Avoid expensive resorts.
        """
    )



# -------------------------------------
# Test 5: Missing Information
# -------------------------------------

def test_missing_information():

    run_test(
        "Missing Information",

        """
        I want to visit Europe.
        """
    )



# -------------------------------------
# Test 6: Hinglish
# -------------------------------------

def test_hinglish():

    run_test(
        "Hinglish Manali Trip",

        """
        Hum 5 dost Manali jana chahte hain.

        Budget 50000 rupees hai.

        5 din ka trip chahiye.

        Adventure activities pasand hain.

        Crowded jagah avoid karni hai.
        """
    )