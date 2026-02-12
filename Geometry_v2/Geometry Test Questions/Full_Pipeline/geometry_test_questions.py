#!/usr/bin/env python3
"""
Synthetic Geometry Test Questions for the Geometry Diagram Pipeline.

These questions test the ORIGINAL prompt path (non-coordinate geometry):
- Stage 1: Question_to_Blueprint (or Question_to_Blueprint_Coordinate_included with 2D/3D output)
- Stage 2: Blueprint_to_Code_Gemini

10 questions organized by dimension and topic:
- 2D: triangles, circles, quadrilaterals (5 questions)
- 3D: prisms, pyramids, cylinders (5 questions)

Usage:
    Import this module in batch_test.py and use GEOMETRY_TEST_QUESTIONS list.

    python3 batch_test.py --test-set geometry              # Run all 2D + 3D
    python3 batch_test.py --test-set geometry --topic 2d   # Run only 2D
    python3 batch_test.py --test-set geometry --topic 3d   # Run only 3D
"""

# ======================================================================
# 2D Synthetic Geometry Questions
# ======================================================================

TEST_QUESTIONS_2D = [
    {
        "id": "2d_01",
        "name": "Right Triangle Area",
        "text": "In triangle ABC, angle ACB = 90 degrees, AC = 24cm, BC = 12cm. D is a point on AC such that AD = 12cm. E is a point on AB such that DE is perpendicular to AC. Find the area of triangle ADE.",
        "expected_type": "2d",
        "topic": "triangles",
    },
    {
        "id": "2d_02",
        "name": "Circle Tangent",
        "text": "A circle with center O has radius 5cm. Point P is outside the circle such that OP = 13cm. A tangent from P touches the circle at point T. Find the length of PT.",
        "expected_type": "2d",
        "topic": "circles",
    },
    {
        "id": "2d_03",
        "name": "Parallelogram Diagonals",
        "text": "In parallelogram ABCD, AB = 8cm, BC = 6cm, and angle ABC = 60 degrees. The diagonals AC and BD intersect at point E. Find the length of AC.",
        "expected_type": "2d",
        "topic": "quadrilaterals",
    },
    {
        "id": "2d_04",
        "name": "Inscribed Angle",
        "text": "In a circle with center O and radius 10cm, chord AB has length 12cm. Point C is on the major arc AB. Find angle ACB.",
        "expected_type": "2d",
        "topic": "circles",
    },
    {
        "id": "2d_05",
        "name": "Similar Triangles",
        "text": "In triangle ABC, D is on AB and E is on AC such that DE is parallel to BC. If AD = 4cm, DB = 6cm, and BC = 15cm, find the length of DE.",
        "expected_type": "2d",
        "topic": "triangles",
    },
]

# ======================================================================
# 3D Synthetic Geometry Questions
# ======================================================================

TEST_QUESTIONS_3D = [
    {
        "id": "3d_01",
        "name": "Triangular Prism Diagonal",
        "text": "A triangular prism has a right-angled triangle as its base with legs AB = 3cm and BC = 4cm (angle ABC = 90 degrees). The height of the prism AD = 10cm. Find the length of the space diagonal AF where F is directly above C.",
        "expected_type": "3d",
        "topic": "prisms",
    },
    {
        "id": "3d_02",
        "name": "Rectangular Box Diagonal",
        "text": "A rectangular box has dimensions length = 12cm, width = 5cm, and height = 4cm. Find the length of the space diagonal from one corner to the opposite corner.",
        "expected_type": "3d",
        "topic": "prisms",
    },
    {
        "id": "3d_03",
        "name": "Pyramid Height",
        "text": "A square pyramid has a base with side length 6cm. The apex P is directly above the center of the base at height 8cm. Find the slant height from P to the midpoint of one base edge.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "3d_04",
        "name": "Tetrahedron Edge",
        "text": "A regular tetrahedron ABCD has all edges equal to 6cm. Point M is the midpoint of edge AB. Find the distance from M to vertex D.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "3d_05",
        "name": "Cylinder Diagonal",
        "text": "A cylinder has radius 3cm and height 8cm. Point A is on the top circle and point B is on the bottom circle, diametrically opposite to A. Find the straight-line distance from A to B.",
        "expected_type": "3d",
        "topic": "cylinders",
    },
]

# ======================================================================
# Combined list
# ======================================================================

GEOMETRY_TEST_QUESTIONS = TEST_QUESTIONS_2D + TEST_QUESTIONS_3D

# ======================================================================
# Helper functions
# ======================================================================

def get_questions_by_dimension(dimension):
    # type: (str) -> list
    """Filter questions by dimension (2d, 3d, or all).

    Args:
        dimension: One of '2d', '3d', or 'all'.

    Returns:
        List of question dicts matching the dimension.
    """
    if dimension == "all":
        return GEOMETRY_TEST_QUESTIONS
    elif dimension == "2d":
        return TEST_QUESTIONS_2D
    elif dimension == "3d":
        return TEST_QUESTIONS_3D
    return GEOMETRY_TEST_QUESTIONS


def get_questions_by_topic(topic):
    # type: (str) -> list
    """Filter questions by topic.

    Args:
        topic: One of 'triangles', 'circles', 'quadrilaterals',
               'prisms', 'pyramids', 'cylinders', or 'all'.

    Returns:
        List of question dicts matching the topic.
    """
    if topic == "all":
        return GEOMETRY_TEST_QUESTIONS
    return [q for q in GEOMETRY_TEST_QUESTIONS if q["topic"] == topic]


def get_all_topics():
    # type: () -> list
    """Get list of all unique topics."""
    return list(set(q["topic"] for q in GEOMETRY_TEST_QUESTIONS))


# ======================================================================
# Quick summary when run directly
# ======================================================================

if __name__ == "__main__":
    print("Synthetic Geometry Test Questions (2D + 3D)")
    print("=" * 50)
    print(f"Total questions: {len(GEOMETRY_TEST_QUESTIONS)}")
    print(f"  - 2D questions: {len(TEST_QUESTIONS_2D)}")
    print(f"  - 3D questions: {len(TEST_QUESTIONS_3D)}")
    print()

    print("2D Questions:")
    for q in TEST_QUESTIONS_2D:
        print(f"  - {q['id']}: {q['name']} ({q['topic']})")

    print("\n3D Questions:")
    for q in TEST_QUESTIONS_3D:
        print(f"  - {q['id']}: {q['name']} ({q['topic']})")

    print(f"\nTopics: {', '.join(sorted(get_all_topics()))}")
