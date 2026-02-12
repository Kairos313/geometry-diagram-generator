#!/usr/bin/env python3
"""
HKDSE Grade 12 Geometry Test Questions for the Geometry Diagram Pipeline.

These questions are based on Hong Kong Diploma of Secondary Education (HKDSE)
Mathematics Extended Part Module 2 style problems.

Topics covered:
- 2D: Circle theorems, similar triangles, trigonometry, cyclic quadrilaterals
- 3D: Pyramids, prisms, angles between lines/planes, tetrahedra

Usage:
    Import this module in batch_test.py and use HKDSE_TEST_QUESTIONS list.

    python3 batch_test.py --test-set hkdse              # Run all 2D + 3D
    python3 batch_test.py --test-set hkdse --topic 2d   # Run only 2D
    python3 batch_test.py --test-set hkdse --topic 3d   # Run only 3D
"""

# ======================================================================
# 2D HKDSE-Style Geometry Questions
# ======================================================================

HKDSE_QUESTIONS_2D = [
    # --- Circle Theorems ---
    {
        "id": "hkdse_2d_01",
        "name": "Cyclic Quadrilateral Angles",
        "text": "ABCD is a cyclic quadrilateral inscribed in a circle with center O. Given that angle DAB = 75 degrees and angle ABC = 110 degrees, find angle BCD.",
        "expected_type": "2d",
        "topic": "circles",
    },
    {
        "id": "hkdse_2d_02",
        "name": "Tangent-Chord Angle",
        "text": "In a circle with center O, TA is a tangent to the circle at point A. Chord AB makes an angle of 35 degrees with the tangent TA. Point C is on the major arc AB. Find angle ACB.",
        "expected_type": "2d",
        "topic": "circles",
    },
    {
        "id": "hkdse_2d_03",
        "name": "Two Tangents from External Point",
        "text": "Two tangents PA and PB are drawn from an external point P to a circle with center O and radius 6cm. If angle APB = 60 degrees, find the length of PA.",
        "expected_type": "2d",
        "topic": "circles",
    },
    # --- Similar Triangles ---
    {
        "id": "hkdse_2d_04",
        "name": "Similar Triangles Ratio",
        "text": "In triangle ABC, D is on AB and E is on AC such that DE is parallel to BC. If AD = 6cm, DB = 4cm, and the area of triangle ADE is 27 square cm, find the area of trapezium BCED.",
        "expected_type": "2d",
        "topic": "triangles",
    },
    {
        "id": "hkdse_2d_05",
        "name": "Altitude and Similar Triangles",
        "text": "In right-angled triangle ABC with the right angle at C, CD is the altitude from C to the hypotenuse AB. If AD = 4cm and DB = 9cm, find the length of CD.",
        "expected_type": "2d",
        "topic": "triangles",
    },
    # --- Trigonometry in Triangles ---
    {
        "id": "hkdse_2d_06",
        "name": "Cosine Rule Application",
        "text": "In triangle PQR, PQ = 7cm, QR = 8cm, and angle PQR = 120 degrees. Find the length of PR.",
        "expected_type": "2d",
        "topic": "triangles",
    },
    {
        "id": "hkdse_2d_07",
        "name": "Sine Rule for Circumradius",
        "text": "In triangle ABC, angle BAC = 45 degrees, and BC = 10cm. Find the radius of the circumscribed circle.",
        "expected_type": "2d",
        "topic": "triangles",
    },
    # --- Quadrilaterals ---
    {
        "id": "hkdse_2d_08",
        "name": "Rhombus Diagonals",
        "text": "In rhombus ABCD, the diagonals AC and BD intersect at point E. If AC = 16cm and BD = 12cm, find the length of side AB.",
        "expected_type": "2d",
        "topic": "quadrilaterals",
    },
    {
        "id": "hkdse_2d_09",
        "name": "Trapezium Midsegment",
        "text": "In trapezium ABCD, AB is parallel to DC. AB = 14cm and DC = 8cm. E and F are midpoints of AD and BC respectively. Find the length of EF.",
        "expected_type": "2d",
        "topic": "quadrilaterals",
    },
    {
        "id": "hkdse_2d_10",
        "name": "Angle Bisector Theorem",
        "text": "In triangle ABC, AB = 12cm, AC = 8cm, and BC = 10cm. The angle bisector from A meets BC at point D. Find the length of BD.",
        "expected_type": "2d",
        "topic": "triangles",
    },
]

# ======================================================================
# 3D HKDSE-Style Geometry Questions
# ======================================================================

HKDSE_QUESTIONS_3D = [
    # --- Pyramids ---
    {
        "id": "hkdse_3d_01",
        "name": "Square Pyramid Slant Height",
        "text": "A right square pyramid VABCD has a square base ABCD with side length 8cm. The apex V is directly above the center of the base at height 6cm. Find the slant height from V to the midpoint of edge AB.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "hkdse_3d_02",
        "name": "Triangular Pyramid Volume",
        "text": "In tetrahedron VABC, the base ABC is an equilateral triangle with side 6cm. VA = VB = VC = 8cm. V is directly above the centroid of triangle ABC. Find the height of the tetrahedron.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "hkdse_3d_03",
        "name": "Pyramid Angle with Base",
        "text": "A right pyramid has a rectangular base ABCD where AB = 6cm and BC = 8cm. The apex V is 12cm directly above the center of the base. Find the angle that edge VA makes with the base plane.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    # --- Prisms ---
    {
        "id": "hkdse_3d_04",
        "name": "Triangular Prism Diagonal",
        "text": "A right triangular prism has a base triangle ABC where angle BAC = 90 degrees, AB = 3cm, and AC = 4cm. The height of the prism is 12cm. D, E, F are directly above A, B, C respectively. Find the length of diagonal BF.",
        "expected_type": "3d",
        "topic": "prisms",
    },
    {
        "id": "hkdse_3d_05",
        "name": "Cuboid Space Diagonal",
        "text": "A cuboid ABCDEFGH has dimensions AB = 8cm, BC = 6cm, and CG = 10cm. Find the length of the space diagonal AG.",
        "expected_type": "3d",
        "topic": "prisms",
    },
    # --- Angles Between Lines and Planes ---
    {
        "id": "hkdse_3d_06",
        "name": "Angle Between Line and Plane",
        "text": "In a cube ABCDEFGH with side 4cm, where ABCD is the bottom face and EFGH is the top face with E above A. Find the angle that diagonal AG makes with the base plane ABCD.",
        "expected_type": "3d",
        "topic": "prisms",
    },
    {
        "id": "hkdse_3d_07",
        "name": "Dihedral Angle in Pyramid",
        "text": "A regular tetrahedron ABCD has all edges equal to 6cm. Find the dihedral angle between faces ABC and ABD.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    # --- Distance Problems ---
    {
        "id": "hkdse_3d_08",
        "name": "Distance from Point to Plane",
        "text": "In a right pyramid VABCD with square base ABCD of side 10cm and apex V at height 12cm above the center, M is the midpoint of edge VA. Find the perpendicular distance from M to the base plane.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "hkdse_3d_09",
        "name": "Shortest Path on Surface",
        "text": "A cylinder has radius 3cm and height 8cm. Point A is on the top circle and point B is on the bottom circle, directly below A. An ant crawls from A to B along the curved surface. Find the shortest distance the ant travels.",
        "expected_type": "3d",
        "topic": "cylinders",
    },
    {
        "id": "hkdse_3d_10",
        "name": "Cone Slant Height",
        "text": "A right circular cone has base radius 5cm and height 12cm. The apex is V and A is a point on the circumference of the base. Find the slant height VA.",
        "expected_type": "3d",
        "topic": "cones",
    },
]

# ======================================================================
# Advanced HKDSE M2-Style Questions (Section B difficulty)
# Based on typical HKDSE M2 past paper patterns
# ======================================================================

HKDSE_ADVANCED_2D = [
    # --- Advanced Circle Theorems ---
    {
        "id": "hkdse_adv_2d_01",
        "name": "Secants and Tangent from External Point",
        "text": "From a point P outside a circle with center O, two secants are drawn: one passes through points A and B on the circle (with A between P and B) such that PA = 3cm and PB = 8cm, and another passes through points C and D on the circle (with C between P and D) such that PC = 4cm. A tangent from P touches the circle at point T. Find the length of PD and the length of the tangent PT.",
        "expected_type": "2d",
        "topic": "circles",
    },
    {
        "id": "hkdse_adv_2d_02",
        "name": "Incircle of Triangle",
        "text": "Triangle ABC has sides AB = 13cm, BC = 14cm, and CA = 15cm. The incircle touches BC at point D. Find the length of BD and the radius of the incircle.",
        "expected_type": "2d",
        "topic": "circles",
    },
    {
        "id": "hkdse_adv_2d_03",
        "name": "Power of a Point",
        "text": "From an external point P, a secant PAB passes through a circle where A and B are on the circle with PA = 4cm and AB = 5cm. Another secant PCD passes through the same circle with PC = 3cm. Find the length of CD.",
        "expected_type": "2d",
        "topic": "circles",
    },
    # --- Advanced Triangle Geometry ---
    {
        "id": "hkdse_adv_2d_04",
        "name": "Orthocenter and Circumcenter",
        "text": "In triangle ABC, A is at (0, 6), B is at (0, 0), and C is at (8, 0). Find the coordinates of the orthocenter H and verify that the circumcenter O, centroid G, and orthocenter H are collinear.",
        "expected_type": "2d",
        "topic": "triangles",
    },
    {
        "id": "hkdse_adv_2d_05",
        "name": "Menelaus Theorem",
        "text": "In triangle ABC, point D lies on side BC and point E lies on side CA such that D, E, and a point F on line AB (or its extension) are collinear. If BD = 2cm, DC = 3cm, CE = 4cm, EA = 2cm, find the ratio AF:FB.",
        "expected_type": "2d",
        "topic": "triangles",
    },
]

HKDSE_ADVANCED_3D = [
    # --- Vector-based 3D Geometry (M2 Section B style) ---
    {
        "id": "hkdse_adv_3d_01",
        "name": "Tetrahedron with Perpendicular Edges",
        "text": "OABC is a tetrahedron where OA is perpendicular to both OB and OC. OA = 6cm, OB = 8cm, OC = 10cm, and angle BOC = 60 degrees. Find the area of triangle ABC and the volume of the tetrahedron.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "hkdse_adv_3d_02",
        "name": "Plane Equation and Distance",
        "text": "A tetrahedron OABC has vertices O at the origin, A at (4, 0, 0), B at (0, 3, 0), and C at (0, 0, 6). Find the equation of plane ABC and the perpendicular distance from O to this plane.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "hkdse_adv_3d_03",
        "name": "Angle Between Two Planes",
        "text": "In tetrahedron VABC, the base ABC is an equilateral triangle with side 8cm. V is directly above the centroid of ABC at height 10cm. Find the dihedral angle between face VAB and the base ABC.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "hkdse_adv_3d_04",
        "name": "Perpendicular from Vertex to Opposite Edge",
        "text": "In tetrahedron ABCD, A is at (0, 0, 0), B at (6, 0, 0), C at (3, 5, 0), and D at (2, 2, 8). Find the foot of the perpendicular from D to edge AB and the length of this perpendicular.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "hkdse_adv_3d_05",
        "name": "Midpoint Plane in Prism",
        "text": "A triangular prism has vertices A at (0, 0, 0), B at (6, 0, 0), C at (0, 4, 0), and the top vertices D, E, F directly above A, B, C at height 9cm. M is the midpoint of edge CF. Find the angle between line AM and the base plane ABC.",
        "expected_type": "3d",
        "topic": "prisms",
    },
    {
        "id": "hkdse_adv_3d_06",
        "name": "Cross Section of Pyramid",
        "text": "A square pyramid VABCD has a base with side 10cm and apex V at height 15cm above the center. A horizontal plane cuts the pyramid at height 6cm above the base. Find the area of the cross section.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "hkdse_adv_3d_07",
        "name": "Shortest Distance Between Skew Lines",
        "text": "In a cube ABCDEFGH with side 6cm, where ABCD is the bottom face and E is above A. Find the shortest distance between the skew lines AH and BF.",
        "expected_type": "3d",
        "topic": "prisms",
    },
    {
        "id": "hkdse_adv_3d_08",
        "name": "Angle Between Face Diagonal and Space Diagonal",
        "text": "In a rectangular box with dimensions 3cm by 4cm by 12cm, find the angle between a face diagonal on the 3x4 face and the space diagonal of the box.",
        "expected_type": "3d",
        "topic": "prisms",
    },
    {
        "id": "hkdse_adv_3d_09",
        "name": "Circumsphere of Tetrahedron",
        "text": "A regular tetrahedron ABCD has all edges equal to 12cm. Find the radius of the circumsphere (the sphere passing through all four vertices).",
        "expected_type": "3d",
        "topic": "pyramids",
    },
    {
        "id": "hkdse_adv_3d_10",
        "name": "Projection onto Plane",
        "text": "In a right pyramid VABCD with square base ABCD of side 8cm and height 12cm, the apex V is directly above the center O. Point P is on edge VA such that VP:PA = 1:2. Find the area of the projection of triangle VBC onto the base plane.",
        "expected_type": "3d",
        "topic": "pyramids",
    },
]

# ======================================================================
# Combined lists
# ======================================================================

# Basic questions only (original set)
HKDSE_BASIC_QUESTIONS = HKDSE_QUESTIONS_2D + HKDSE_QUESTIONS_3D

# All 2D questions (basic + advanced)
HKDSE_ALL_2D = HKDSE_QUESTIONS_2D + HKDSE_ADVANCED_2D

# All 3D questions (basic + advanced)
HKDSE_ALL_3D = HKDSE_QUESTIONS_3D + HKDSE_ADVANCED_3D

# All questions combined (basic + advanced)
HKDSE_TEST_QUESTIONS = HKDSE_ALL_2D + HKDSE_ALL_3D

# ======================================================================
# Helper functions
# ======================================================================

def get_questions_by_dimension(dimension, include_advanced=True):
    # type: (str, bool) -> list
    """Filter questions by dimension (2d, 3d, or all).

    Args:
        dimension: One of '2d', '3d', or 'all'.
        include_advanced: If True, include advanced M2-style questions.

    Returns:
        List of question dicts matching the dimension.
    """
    if include_advanced:
        if dimension == "all":
            return HKDSE_TEST_QUESTIONS
        elif dimension == "2d":
            return HKDSE_ALL_2D
        elif dimension == "3d":
            return HKDSE_ALL_3D
    else:
        if dimension == "all":
            return HKDSE_BASIC_QUESTIONS
        elif dimension == "2d":
            return HKDSE_QUESTIONS_2D
        elif dimension == "3d":
            return HKDSE_QUESTIONS_3D
    return HKDSE_TEST_QUESTIONS


def get_questions_by_topic(topic):
    # type: (str) -> list
    """Filter questions by topic.

    Args:
        topic: One of 'circles', 'triangles', 'quadrilaterals',
               'pyramids', 'prisms', 'cylinders', 'cones', or 'all'.

    Returns:
        List of question dicts matching the topic.
    """
    if topic == "all":
        return HKDSE_TEST_QUESTIONS
    return [q for q in HKDSE_TEST_QUESTIONS if q["topic"] == topic]


def get_all_topics():
    # type: () -> list
    """Get list of all unique topics."""
    return list(set(q["topic"] for q in HKDSE_TEST_QUESTIONS))


# ======================================================================
# Quick summary when run directly
# ======================================================================

if __name__ == "__main__":
    print("HKDSE Grade 12 Geometry Test Questions")
    print("=" * 50)
    print(f"Total questions: {len(HKDSE_TEST_QUESTIONS)}")
    print(f"  - 2D questions: {len(HKDSE_ALL_2D)} (basic: {len(HKDSE_QUESTIONS_2D)}, advanced: {len(HKDSE_ADVANCED_2D)})")
    print(f"  - 3D questions: {len(HKDSE_ALL_3D)} (basic: {len(HKDSE_QUESTIONS_3D)}, advanced: {len(HKDSE_ADVANCED_3D)})")
    print()

    print("Basic 2D Questions:")
    for q in HKDSE_QUESTIONS_2D:
        print(f"  - {q['id']}: {q['name']} ({q['topic']})")

    print("\nAdvanced 2D Questions (M2 Section B style):")
    for q in HKDSE_ADVANCED_2D:
        print(f"  - {q['id']}: {q['name']} ({q['topic']})")

    print("\nBasic 3D Questions:")
    for q in HKDSE_QUESTIONS_3D:
        print(f"  - {q['id']}: {q['name']} ({q['topic']})")

    print("\nAdvanced 3D Questions (M2 Section B style):")
    for q in HKDSE_ADVANCED_3D:
        print(f"  - {q['id']}: {q['name']} ({q['topic']})")

    print(f"\nTopics: {', '.join(sorted(get_all_topics()))}")
