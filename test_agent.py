# test_production_agent.py

import time
import traceback
from pprint import pprint

from app.agent import ProductionAgent
from langchain_core.messages import HumanMessage


def print_header(title: str):
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)


def print_section(title: str):
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


def main():
    print_header("PRODUCTION AGENT TEST SUITE")

    # ------------------------------------------------------------------
    # AGENT INITIALIZATION
    # ------------------------------------------------------------------
    print_section("1. INITIALIZING AGENT")

    try:
        agent = ProductionAgent()
        print("✅ Agent initialized successfully")
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        traceback.print_exc()
        return

    # ------------------------------------------------------------------
    # GRAPH VISUALIZATION
    # ------------------------------------------------------------------
    print_section("2. GRAPH STRUCTURE")

    try:
        print(agent.graph.get_graph().draw_ascii())
    except Exception as e:
        print(f"⚠ Could not draw graph: {e}")

    # ------------------------------------------------------------------
    # TEST QUERIES
    # ------------------------------------------------------------------
    test_queries = [
        "Hello",
        "What is LangGraph?",
        "Explain RAG architecture in simple terms.",
        "Write a Python function to reverse a linked list.",
        "What is the difference between Kafka and RabbitMQ?"
    ]

    print_section("3. AGENT RESPONSE TESTS")

    passed = 0
    failed = 0

    for idx, query in enumerate(test_queries, start=1):

        print("\n" + "#" * 80)
        print(f"TEST CASE #{idx}")
        print("#" * 80)

        print(f"\nUSER QUERY:\n{query}")

        start_time = time.perf_counter()

        try:
            result = agent.invoke(query)

            end_time = time.perf_counter()

            print("\nRESPONSE:")
            print(result["response"])

            print("\nMETADATA:")
            print(f"Model Used : {result['model_used']}")
            print(f"Error      : {result['error']}")
            print(f"Time Taken : {end_time-start_time:.2f} sec")

            passed += 1

        except Exception as e:
            end_time = time.perf_counter()

            print("\n❌ TEST FAILED")
            print(str(e))
            traceback.print_exc()

            print(f"\nTime Taken : {end_time-start_time:.2f} sec")

            failed += 1

    # ------------------------------------------------------------------
    # RAW GRAPH INVOCATION TEST
    # ------------------------------------------------------------------
    print_section("4. RAW LANGGRAPH STATE TEST")

    try:
        state = agent.graph.invoke(
            {
                "messages": [
                    HumanMessage(content="What is LangGraph?")
                ],
                "error": None,
                "retry_count": 0,
                "model_used": "",
            }
        )

        print("✅ Raw graph execution successful")

        print("\nFULL STATE:")
        pprint(state)

    except Exception as e:
        print("❌ Raw graph execution failed")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # MEMORY TEST
    # ------------------------------------------------------------------
    print_section("5. MEMORY TEST")

    print(
        "NOTE: Current implementation does NOT persist memory "
        "between invocations."
    )

    try:
        response1 = agent.invoke("My name is Anurag")
        response2 = agent.invoke("What is my name?")

        print("\nTURN 1 RESPONSE:")
        print(response1["response"])

        print("\nTURN 2 RESPONSE:")
        print(response2["response"])

    except Exception as e:
        print("❌ Memory test failed")
        traceback.print_exc()

    # ------------------------------------------------------------------
    # FINAL REPORT
    # ------------------------------------------------------------------
    print_header("TEST SUMMARY")

    print(f"Total Tests : {len(test_queries)}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {failed}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED")
    else:
        print("\n⚠ SOME TESTS FAILED")


if __name__ == "__main__":
    main()