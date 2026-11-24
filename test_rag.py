from services.rag_engine import load_knowledge, retrieve_knowledge

def test_rag():
    print("===== LOADING KNOWLEDGE BASE =====")
    docs = load_knowledge()
    print(f"Total knowledge passages loaded: {len(docs)}")
    assert len(docs) >= 5, "Knowledge base should contain at least 5 passages"

    # Main test query from user requirements
    query = "What are the trade-offs of replacing a steel door panel with aluminum?"
    print(f"\n===== TEST 1: CORE TRADE-OFF QUERY =====")
    print(f"Query: \"{query}\"\n")

    results = retrieve_knowledge(query, top_k=3)
    print(f"Retrieved {len(results)} relevant passages:\n")

    for i, res in enumerate(results, start=1):
        print(f"--- Result {i} (Similarity Score: {res['similarity_score']:.4f}) ---")
        print(f"Source Title: {res['source_title']}")
        print(f"Section:      {res['section']}")
        print(f"Source File:  {res['source_file']}")
        print(f"Notice:       {res['disclaimer']}")
        print("Passage Content:")
        print(res['content'][:250] + ("..." if len(res['content']) > 250 else ""))
        print()

    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    assert any("steel" in r['content'].lower() and "aluminum" in r['content'].lower() for r in results)

    # Additional queries covering other required topics
    additional_queries = [
        ("Automotive manufacturing processes like stamping and injection molding", "manufacturing"),
        ("How does lightweighting impact electric vehicle battery range?", "lightweighting"),
        ("Material selection factors including corrosion, durability and strength", "selection"),
        ("Material weight and cost trade-offs in automotive engineering", "trade-offs")
    ]

    print("===== TEST 2: ADDITIONAL TOPIC QUERIES =====")
    for q, topic in additional_queries:
        res = retrieve_knowledge(q, top_k=2)
        print(f"\nQuery: '{q}'")
        for r in res:
            print(f"  -> [{r['source_file']}] {r['source_title']} - {r['section']} (Score: {r['similarity_score']:.4f})")
        assert len(res) > 0, f"Expected results for topic: {topic}"

    print("\n===== ALL RAG TESTS PASSED SUCCESSFULLY =====")

if __name__ == "__main__":
    test_rag()
