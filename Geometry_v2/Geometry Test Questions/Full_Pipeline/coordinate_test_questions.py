#!/usr/bin/env python3
"""
Coordinate Geometry Test Questions for the Geometry Diagram Pipeline.

15 questions covering 6 HKDSE topics:
- Straight lines (3 questions)
- Circles (4 questions)
- Linear programming (2 questions)
- Loci (2 questions)
- Graph transformations (2 questions)
- Functions & graphs (2 questions)

Usage:
    Import this module in batch_test.py and use COORDINATE_TEST_QUESTIONS list.
"""

# ======================================================================
# Test Questions organized by HKDSE topic
# ======================================================================

COORDINATE_TEST_QUESTIONS = [
    # -------------------------------------------------------------------------
    # EQUATIONS OF STRAIGHT LINES (Unit 10)
    # -------------------------------------------------------------------------
    {
        "id": "coord_01",
        "name": "Line Through Two Points",
        "text": "Find the equation of the straight line passing through A(2, 3) and B(6, -1). Sketch the line and mark the x-intercept and y-intercept.",
        "expected_type": "coordinate_2d",
        "topic": "straight_lines",
    },
    {
        "id": "coord_02",
        "name": "Intersection of Two Lines",
        "text": "Two lines L1: 2x + y = 8 and L2: x - y = 1 intersect at point P. Find P and sketch both lines.",
        "expected_type": "coordinate_2d",
        "topic": "straight_lines",
    },
    {
        "id": "coord_03",
        "name": "Perpendicular Line",
        "text": "The line L passes through A(1, 4) and is perpendicular to the line 3x - y + 2 = 0. Find the equation of L and sketch both lines.",
        "expected_type": "coordinate_2d",
        "topic": "straight_lines",
    },

    # -------------------------------------------------------------------------
    # EQUATIONS OF CIRCLES (Unit 13)
    # -------------------------------------------------------------------------
    {
        "id": "coord_04",
        "name": "Circle from Centre and Point",
        "text": "A circle has centre C(3, -2) and passes through the point A(7, 1). Find the equation of the circle and sketch it.",
        "expected_type": "coordinate_2d",
        "topic": "circles",
    },
    {
        "id": "coord_05",
        "name": "Circle from General Form",
        "text": "The equation of a circle is x^2 + y^2 - 6x + 4y - 12 = 0. Find the centre and radius, then sketch the circle.",
        "expected_type": "coordinate_2d",
        "topic": "circles",
    },
    {
        "id": "coord_06",
        "name": "Line-Circle Intersection",
        "text": "A circle C: (x-2)^2 + (y-3)^2 = 25 and the line L: y = x + 4. Find the points of intersection and determine whether L is a tangent, secant, or misses the circle. Sketch the diagram.",
        "expected_type": "coordinate_2d",
        "topic": "circles",
    },
    {
        "id": "coord_07",
        "name": "Tangent to Circle",
        "text": "Find the equation of the tangent to the circle x^2 + y^2 = 25 at the point (3, 4). Sketch the circle and the tangent line.",
        "expected_type": "coordinate_2d",
        "topic": "circles",
    },

    # -------------------------------------------------------------------------
    # LINEAR PROGRAMMING (Unit 8)
    # -------------------------------------------------------------------------
    {
        "id": "coord_08",
        "name": "Basic Linear Programming",
        "text": "Maximize P = 5x + 4y subject to: x + y <= 6, 2x + y <= 10, x >= 0, y >= 0. Sketch the feasible region and find the optimal point.",
        "expected_type": "coordinate_2d",
        "topic": "linear_programming",
    },
    {
        "id": "coord_09",
        "name": "Word Problem LP",
        "text": "A company makes products A and B. Each unit of A requires 2 hours of labour and 1 kg of material. Each unit of B requires 1 hour of labour and 2 kg of material. Available: 100 hours, 80 kg. Profit: $30 per A, $20 per B. Maximize profit. Sketch the constraints and feasible region.",
        "expected_type": "coordinate_2d",
        "topic": "linear_programming",
    },

    # -------------------------------------------------------------------------
    # LOCI (Unit 12)
    # -------------------------------------------------------------------------
    {
        "id": "coord_10",
        "name": "Perpendicular Bisector Locus",
        "text": "A point P moves such that PA = PB where A = (1, 3) and B = (5, 1). Find the equation of the locus of P and sketch it.",
        "expected_type": "coordinate_2d",
        "topic": "loci",
    },
    {
        "id": "coord_11",
        "name": "Circle Locus",
        "text": "A point P moves such that its distance from the point A(2, 0) is always 5 units. Find the equation of the locus of P and sketch it.",
        "expected_type": "coordinate_2d",
        "topic": "loci",
    },

    # -------------------------------------------------------------------------
    # GRAPH TRANSFORMATIONS (Unit 9)
    # -------------------------------------------------------------------------
    {
        "id": "coord_12",
        "name": "Absolute Value Graph",
        "text": "Sketch the graph of y = |2x - 3| and find the coordinates of the vertex.",
        "expected_type": "coordinate_2d",
        "topic": "graph_transformations",
    },
    {
        "id": "coord_13",
        "name": "Function Transformation",
        "text": "The graph of y = f(x) = x^2 is transformed to y = 2f(x-1) + 3. Sketch both the original and transformed graphs on the same axes.",
        "expected_type": "coordinate_2d",
        "topic": "graph_transformations",
    },

    # -------------------------------------------------------------------------
    # FUNCTIONS & GRAPHS (Unit 2, 3)
    # -------------------------------------------------------------------------
    {
        "id": "coord_14",
        "name": "Exponential and Log Graphs",
        "text": "Sketch the graph of y = 2^x and y = log_2(x) on the same coordinate plane. Mark their relationship to the line y = x.",
        "expected_type": "coordinate_2d",
        "topic": "functions",
    },
    {
        "id": "coord_15",
        "name": "Quadratic Graph",
        "text": "Sketch the graph of y = x^2 - 4x + 3. Mark the vertex, axis of symmetry, y-intercept, and x-intercepts.",
        "expected_type": "coordinate_2d",
        "topic": "functions",
    },
]

# ======================================================================
# Helper functions
# ======================================================================

def get_questions_by_topic(topic):
    # type: (str) -> list
    """Filter questions by topic.

    Args:
        topic: One of 'straight_lines', 'circles', 'linear_programming',
               'loci', 'graph_transformations', 'functions', or 'all'.

    Returns:
        List of question dicts matching the topic.
    """
    if topic == "all":
        return COORDINATE_TEST_QUESTIONS
    return [q for q in COORDINATE_TEST_QUESTIONS if q["topic"] == topic]


def get_all_topics():
    # type: () -> list
    """Get list of all unique topics."""
    return list(set(q["topic"] for q in COORDINATE_TEST_QUESTIONS))


# ======================================================================
# Quick summary when run directly
# ======================================================================

if __name__ == "__main__":
    print("Coordinate Geometry Test Questions")
    print("=" * 50)
    print(f"Total questions: {len(COORDINATE_TEST_QUESTIONS)}")
    print()

    topics = {}
    for q in COORDINATE_TEST_QUESTIONS:
        topic = q["topic"]
        if topic not in topics:
            topics[topic] = []
        topics[topic].append(q)

    for topic, questions in sorted(topics.items()):
        print(f"\n{topic.replace('_', ' ').title()} ({len(questions)} questions):")
        for q in questions:
            print(f"  - {q['id']}: {q['name']}")
