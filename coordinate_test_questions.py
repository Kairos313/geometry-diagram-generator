#!/usr/bin/env python3
"""
Coordinate Geometry Test Questions for the Geometry Diagram Pipeline.

45 questions covering 2D and 3D coordinate geometry:

2D (30 questions):
  Original (15):
    - Straight lines (3), Circles (4), Linear programming (2),
      Loci (2), Graph transformations (2), Functions (2)
  Advanced (15):
    - Conic sections (5), Parametric curves (2), Polar coordinates (2),
      Advanced loci (2), Coordinate polygons (4)

3D (15 questions):
    - Planes (3), Spheres (3), Polyhedra (5),
      Vectors 3D (3), Parametric 3D (1)

Usage:
    Import this module in batch_test.py and use COORDINATE_TEST_QUESTIONS list.
"""

# ======================================================================
# 2D Questions — Original (HKDSE-level)
# ======================================================================

COORDINATE_QUESTIONS_2D_ORIGINAL = [
    # -------------------------------------------------------------------------
    # EQUATIONS OF STRAIGHT LINES (Unit 10)
    # -------------------------------------------------------------------------
    {
        "id": "coord_01",
        "name": "Line Through Two Points",
        "text": "Find the equation of the straight line passing through A(2, 3) and B(6, -1). Sketch the line and mark the x-intercept and y-intercept.",
        "dimension": "coordinate_2d",
        "topic": "straight_lines",
    },
    {
        "id": "coord_02",
        "name": "Intersection of Two Lines",
        "text": "Two lines L1: 2x + y = 8 and L2: x - y = 1 intersect at point P. Find P and sketch both lines.",
        "dimension": "coordinate_2d",
        "topic": "straight_lines",
    },
    {
        "id": "coord_03",
        "name": "Perpendicular Line",
        "text": "The line L passes through A(1, 4) and is perpendicular to the line 3x - y + 2 = 0. Find the equation of L and sketch both lines.",
        "dimension": "coordinate_2d",
        "topic": "straight_lines",
    },

    # -------------------------------------------------------------------------
    # EQUATIONS OF CIRCLES (Unit 13)
    # -------------------------------------------------------------------------
    {
        "id": "coord_04",
        "name": "Circle from Centre and Point",
        "text": "A circle has centre C(3, -2) and passes through the point A(7, 1). Find the equation of the circle and sketch it.",
        "dimension": "coordinate_2d",
        "topic": "circles",
    },
    {
        "id": "coord_05",
        "name": "Circle from General Form",
        "text": "The equation of a circle is x^2 + y^2 - 6x + 4y - 12 = 0. Find the centre and radius, then sketch the circle.",
        "dimension": "coordinate_2d",
        "topic": "circles",
    },
    {
        "id": "coord_06",
        "name": "Line-Circle Intersection",
        "text": "A circle C: (x-2)^2 + (y-3)^2 = 25 and the line L: y = x + 4. Find the points of intersection and determine whether L is a tangent, secant, or misses the circle. Sketch the diagram.",
        "dimension": "coordinate_2d",
        "topic": "circles",
    },
    {
        "id": "coord_07",
        "name": "Tangent to Circle",
        "text": "Find the equation of the tangent to the circle x^2 + y^2 = 25 at the point (3, 4). Sketch the circle and the tangent line.",
        "dimension": "coordinate_2d",
        "topic": "circles",
    },

    # -------------------------------------------------------------------------
    # LINEAR PROGRAMMING (Unit 8)
    # -------------------------------------------------------------------------
    {
        "id": "coord_08",
        "name": "Basic Linear Programming",
        "text": "Maximize P = 5x + 4y subject to: x + y <= 6, 2x + y <= 10, x >= 0, y >= 0. Sketch the feasible region and find the optimal point.",
        "dimension": "coordinate_2d",
        "topic": "linear_programming",
    },
    {
        "id": "coord_09",
        "name": "Word Problem LP",
        "text": "A company makes products A and B. Each unit of A requires 2 hours of labour and 1 kg of material. Each unit of B requires 1 hour of labour and 2 kg of material. Available: 100 hours, 80 kg. Profit: $30 per A, $20 per B. Maximize profit. Sketch the constraints and feasible region.",
        "dimension": "coordinate_2d",
        "topic": "linear_programming",
    },

    # -------------------------------------------------------------------------
    # LOCI (Unit 12)
    # -------------------------------------------------------------------------
    {
        "id": "coord_10",
        "name": "Perpendicular Bisector Locus",
        "text": "A point P moves such that PA = PB where A = (1, 3) and B = (5, 1). Find the equation of the locus of P and sketch it.",
        "dimension": "coordinate_2d",
        "topic": "loci",
    },
    {
        "id": "coord_11",
        "name": "Circle Locus",
        "text": "A point P moves such that its distance from the point A(2, 0) is always 5 units. Find the equation of the locus of P and sketch it.",
        "dimension": "coordinate_2d",
        "topic": "loci",
    },

    # -------------------------------------------------------------------------
    # GRAPH TRANSFORMATIONS (Unit 9)
    # -------------------------------------------------------------------------
    {
        "id": "coord_12",
        "name": "Absolute Value Graph",
        "text": "Sketch the graph of y = |2x - 3| and find the coordinates of the vertex.",
        "dimension": "coordinate_2d",
        "topic": "graph_transformations",
    },
    {
        "id": "coord_13",
        "name": "Function Transformation",
        "text": "The graph of y = f(x) = x^2 is transformed to y = 2f(x-1) + 3. Sketch both the original and transformed graphs on the same axes.",
        "dimension": "coordinate_2d",
        "topic": "graph_transformations",
    },

    # -------------------------------------------------------------------------
    # FUNCTIONS & GRAPHS (Unit 2, 3)
    # -------------------------------------------------------------------------
    {
        "id": "coord_14",
        "name": "Exponential and Log Graphs",
        "text": "Sketch the graph of y = 2^x and y = log_2(x) on the same coordinate plane. Mark their relationship to the line y = x.",
        "dimension": "coordinate_2d",
        "topic": "functions",
    },
    {
        "id": "coord_15",
        "name": "Quadratic Graph",
        "text": "Sketch the graph of y = x^2 - 4x + 3. Mark the vertex, axis of symmetry, y-intercept, and x-intercepts.",
        "dimension": "coordinate_2d",
        "topic": "functions",
    },
]

# ======================================================================
# 2D Questions — Advanced (university-level)
# ======================================================================

COORDINATE_QUESTIONS_2D_ADVANCED = [
    # -------------------------------------------------------------------------
    # CONIC SECTIONS
    # -------------------------------------------------------------------------
    {
        "id": "coord_16",
        "name": "Ellipse Tangent Line",
        "text": "An ellipse has equation x^2/25 + y^2/9 = 1. Find the equation of the tangent to the ellipse at the point (4, 9/5). Sketch the ellipse, the tangent line, both foci F1 and F2, and the two directrices.",
        "dimension": "coordinate_2d",
        "topic": "conic_sections",
    },
    {
        "id": "coord_17",
        "name": "Hyperbola Asymptotes and Foci",
        "text": "The hyperbola x^2/16 - y^2/9 = 1 has foci F1 and F2. Find the coordinates of the foci, the equations of the asymptotes, and sketch the hyperbola with its asymptotes. Mark the vertices and a point P(5, 9/4) on the curve.",
        "dimension": "coordinate_2d",
        "topic": "conic_sections",
    },
    {
        "id": "coord_18",
        "name": "Parabola Focus-Directrix",
        "text": "A parabola has equation y^2 = 12x. Find the focus F and the directrix. A point P on the parabola has y-coordinate 6. Draw the line from P to F and the perpendicular from P to the directrix. Sketch the complete diagram.",
        "dimension": "coordinate_2d",
        "topic": "conic_sections",
    },
    {
        "id": "coord_19",
        "name": "Ellipse and Line Intersection",
        "text": "The ellipse x^2/36 + y^2/16 = 1 is intersected by the line y = x - 2. Find the two points of intersection P and Q, and calculate the length PQ. Sketch the ellipse, the line, and mark P, Q, and the midpoint M of PQ.",
        "dimension": "coordinate_2d",
        "topic": "conic_sections",
    },
    {
        "id": "coord_20",
        "name": "Rotated Conic Section",
        "text": "The conic 5x^2 + 4xy + 2y^2 = 18 is an ellipse rotated from the standard axes. Find the angle of rotation and the semi-major and semi-minor axes. Sketch the conic with both the original xy-axes and the rotated axes shown.",
        "dimension": "coordinate_2d",
        "topic": "conic_sections",
    },

    # -------------------------------------------------------------------------
    # PARAMETRIC CURVES
    # -------------------------------------------------------------------------
    {
        "id": "coord_21",
        "name": "Parametric Cycloid",
        "text": "A cycloid is given parametrically by x = 3(t - sin(t)), y = 3(1 - cos(t)) for t in [0, 4*pi]. Sketch the curve, marking the cusps at t = 0, 2*pi, 4*pi. Also draw the generating circle of radius 3 at the position t = pi/2.",
        "dimension": "coordinate_2d",
        "topic": "parametric_curves",
    },
    {
        "id": "coord_22",
        "name": "Parametric Lissajous",
        "text": "A Lissajous figure is given by x = 4*sin(3t), y = 3*sin(4t) for t in [0, 2*pi]. Sketch the curve and mark the points where t = 0, pi/6, pi/4, pi/3, pi/2. Show the bounding rectangle [-4, 4] x [-3, 3].",
        "dimension": "coordinate_2d",
        "topic": "parametric_curves",
    },

    # -------------------------------------------------------------------------
    # POLAR COORDINATES
    # -------------------------------------------------------------------------
    {
        "id": "coord_23",
        "name": "Cardioid in Polar",
        "text": "The cardioid r = 2(1 + cos(theta)) is given in polar coordinates. Sketch the cardioid on Cartesian axes and shade the region enclosed. Mark the cusp at the origin and the rightmost point (4, 0). Show the polar axis.",
        "dimension": "coordinate_2d",
        "topic": "polar_coordinates",
    },
    {
        "id": "coord_24",
        "name": "Rose Curve and Circle Intersection",
        "text": "A four-petalled rose curve r = 4*cos(2*theta) intersects the circle r = 2. Find all points of intersection in the range [0, 2*pi]. Sketch both curves on the same Cartesian axes, marking all intersection points.",
        "dimension": "coordinate_2d",
        "topic": "polar_coordinates",
    },

    # -------------------------------------------------------------------------
    # ADVANCED LOCI
    # -------------------------------------------------------------------------
    {
        "id": "coord_25",
        "name": "Involute of a Circle",
        "text": "The involute of a circle of radius 2 centered at the origin is given parametrically by x = 2(cos(t) + t*sin(t)), y = 2(sin(t) - t*cos(t)) for t in [0, 3*pi]. Sketch the involute and the generating circle. Mark the starting point at (2, 0) and draw the tangent line at t = pi.",
        "dimension": "coordinate_2d",
        "topic": "advanced_loci",
    },
    {
        "id": "coord_26",
        "name": "Envelope of Line Family",
        "text": "Consider the family of lines x*cos(alpha) + y*sin(alpha) = 3 for alpha in [0, 2*pi]. The envelope of this family is a circle of radius 3. Sketch 12 member lines at alpha = 0, pi/6, pi/3, ..., 11*pi/6 together with the envelope circle.",
        "dimension": "coordinate_2d",
        "topic": "advanced_loci",
    },

    # -------------------------------------------------------------------------
    # COORDINATE POLYGONS
    # -------------------------------------------------------------------------
    {
        "id": "coord_27",
        "name": "Convex Hull of Point Set",
        "text": "Given the 10 points: A(0,0), B(7,1), C(10,5), D(8,9), E(3,11), F(-2,9), G(-4,5), H(-1,2), I(4,6), J(6,3). Find the convex hull. Sketch all 10 points, draw the convex hull polygon, and shade its interior. Label each vertex of the hull.",
        "dimension": "coordinate_2d",
        "topic": "coordinate_polygons",
    },
    {
        "id": "coord_28",
        "name": "Polygon Area by Shoelace",
        "text": "A hexagon has vertices A(0, 0), B(5, 0), C(7, 3), D(5, 7), E(1, 8), F(-2, 4) in order. Compute its area using the Shoelace formula. Sketch the hexagon with all vertices labeled, diagonals from A drawn to each non-adjacent vertex, and the area of each resulting triangle annotated.",
        "dimension": "coordinate_2d",
        "topic": "coordinate_polygons",
    },
    {
        "id": "coord_29",
        "name": "Triangle Centers in Coordinates",
        "text": "Triangle ABC has vertices A(0, 0), B(14, 0), C(4, 10). Find and plot the centroid G, the circumcenter O, the orthocenter H, and the incenter I. Draw the Euler line through G, O, and H. Sketch the triangle with all four centers marked.",
        "dimension": "coordinate_2d",
        "topic": "coordinate_polygons",
    },
    {
        "id": "coord_30",
        "name": "Affine Transformation of Polygon",
        "text": "A regular pentagon has vertices at P_k = (3*cos(2k*pi/5 + pi/2), 3*sin(2k*pi/5 + pi/2)) for k = 0,1,2,3,4. Apply the affine transformation [x', y'] = [[2, 1], [0.5, 1.5]] * [x, y] + [1, -1]. Sketch both the original pentagon and the transformed image, labeling corresponding vertices.",
        "dimension": "coordinate_2d",
        "topic": "coordinate_polygons",
    },
]

# ======================================================================
# 3D Questions — Coordinate Geometry in 3D
# ======================================================================

COORDINATE_QUESTIONS_3D = [
    # -------------------------------------------------------------------------
    # PLANES
    # -------------------------------------------------------------------------
    {
        "id": "coord_31",
        "name": "Three Planes Intersection",
        "text": "Three planes are given: P1: 2x + y - z = 4, P2: x - y + 2z = 3, P3: 3x + 2y + z = 7. Find the point of intersection of all three planes. Sketch the three planes in 3D and mark the intersection point. Show the normal vector of each plane.",
        "dimension": "coordinate_3d",
        "topic": "planes",
    },
    {
        "id": "coord_32",
        "name": "Plane Through Three Points",
        "text": "Find the equation of the plane through A(1, 2, 3), B(4, 0, 1), and C(2, 3, -1). Then find the perpendicular distance from the origin to this plane. Sketch the plane with the three points labeled, the normal vector, and the perpendicular from O.",
        "dimension": "coordinate_3d",
        "topic": "planes",
    },
    {
        "id": "coord_33",
        "name": "Dihedral Angle Between Planes",
        "text": "Two planes are given: P1: x + 2y - 2z = 6 and P2: 2x - y + 2z = 9. Find the dihedral angle between the two planes and the equation of their line of intersection. Sketch both planes, their line of intersection, and indicate the dihedral angle.",
        "dimension": "coordinate_3d",
        "topic": "planes",
    },

    # -------------------------------------------------------------------------
    # SPHERES
    # -------------------------------------------------------------------------
    {
        "id": "coord_34",
        "name": "Sphere and Plane Intersection",
        "text": "A sphere has equation (x-2)^2 + (y-1)^2 + (z-3)^2 = 25. The plane z = 6 intersects the sphere in a circle. Find the center and radius of this circle of intersection. Sketch the sphere, the cutting plane, and the resulting circle.",
        "dimension": "coordinate_3d",
        "topic": "spheres",
    },
    {
        "id": "coord_35",
        "name": "Two Spheres Intersection",
        "text": "Two spheres S1: x^2 + y^2 + z^2 = 49 and S2: (x-4)^2 + (y-3)^2 + z^2 = 36 intersect in a circle. Find the equation of the plane containing this circle and the radius of the intersection circle. Sketch both spheres and highlight the circle of intersection.",
        "dimension": "coordinate_3d",
        "topic": "spheres",
    },
    {
        "id": "coord_36",
        "name": "Sphere Tangent Plane",
        "text": "A sphere has center C(3, -1, 4) and radius 7. Find the equation of the tangent plane at the point P(3, -1, 11) on the sphere. Also find the tangent plane at Q(10, -1, 4). Sketch the sphere with both tangent planes and their points of tangency.",
        "dimension": "coordinate_3d",
        "topic": "spheres",
    },

    # -------------------------------------------------------------------------
    # POLYHEDRA & SOLIDS (vertex/edge/face based)
    # -------------------------------------------------------------------------
    {
        "id": "coord_37",
        "name": "Tetrahedron Volume",
        "text": "A tetrahedron has vertices A(0, 0, 0), B(4, 0, 0), C(1, 3, 0), and D(2, 1, 5). Find the volume of the tetrahedron. Sketch the tetrahedron in 3D with all four vertices labeled, all six edges drawn, and the four triangular faces shaded. Show the height from D perpendicular to face ABC.",
        "dimension": "coordinate_3d",
        "topic": "polyhedra",
    },
    {
        "id": "coord_38",
        "name": "Frustum from Pyramid",
        "text": "A square pyramid has apex V(0, 0, 8) and base vertices A(4, 4, 0), B(-4, 4, 0), C(-4, -4, 0), D(4, -4, 0). A horizontal cutting plane z = 4 creates a frustum. Find the coordinates of the four new vertices on the cutting plane. Sketch the frustum with both the square base and the smaller square top face, labeling all eight vertices.",
        "dimension": "coordinate_3d",
        "topic": "polyhedra",
    },
    {
        "id": "coord_39",
        "name": "Cross Product Normal Vector",
        "text": "Triangle PQR has vertices P(1, 0, 2), Q(3, 4, 1), R(0, 2, 5). Compute the vectors PQ and PR, then find their cross product n = PQ x PR. Sketch the triangle in 3D with the normal vector n drawn from the centroid of the triangle, and label the vertices, edge vectors, and the normal.",
        "dimension": "coordinate_3d",
        "topic": "polyhedra",
    },

    # -------------------------------------------------------------------------
    # 3D VECTORS & LINES
    # -------------------------------------------------------------------------
    {
        "id": "coord_40",
        "name": "Line-Sphere Intersection",
        "text": "A line passes through the point A(1, 2, 3) with direction vector d = (2, -1, 2). A sphere has center C(7, 0, 7) and radius 5. Find the two points where the line intersects the sphere. Sketch the line, the sphere, and mark the two intersection points P and Q.",
        "dimension": "coordinate_3d",
        "topic": "vectors_3d",
    },
    {
        "id": "coord_41",
        "name": "Skew Lines Shortest Distance",
        "text": "Line L1 passes through (1, 0, -1) with direction (2, 1, 3). Line L2 passes through (3, 2, 0) with direction (1, -1, 2). Show that L1 and L2 are skew lines. Find the shortest distance between them and the two closest points. Sketch both lines in 3D with the common perpendicular segment.",
        "dimension": "coordinate_3d",
        "topic": "vectors_3d",
    },
    {
        "id": "coord_42",
        "name": "Projection onto Plane",
        "text": "The point P(5, 7, 3) is projected orthogonally onto the plane 2x + 3y + 6z = 28. Find the foot of the perpendicular Q and the distance PQ. Also reflect P across the plane to find P'. Sketch the plane, the point P, the foot Q, and the reflection P' with the perpendicular line segment.",
        "dimension": "coordinate_3d",
        "topic": "vectors_3d",
    },

    # -------------------------------------------------------------------------
    # PARAMETRIC 3D SURFACES & CURVES
    # -------------------------------------------------------------------------
    {
        "id": "coord_43",
        "name": "Helix in 3D",
        "text": "A circular helix is given by r(t) = (3*cos(t), 3*sin(t), t) for t in [0, 6*pi]. Sketch the helix and the cylinder x^2 + y^2 = 9 on which it lies. Show the tangent vector at t = pi/2. Mark the starting point (3, 0, 0) and the endpoint (3, 0, 6*pi).",
        "dimension": "coordinate_3d",
        "topic": "parametric_3d",
    },
    {
        "id": "coord_44",
        "name": "Octahedron Vertices and Edges",
        "text": "A regular octahedron has vertices at (3, 0, 0), (-3, 0, 0), (0, 3, 0), (0, -3, 0), (0, 0, 3), (0, 0, -3). Sketch the octahedron in 3D with all 6 vertices labeled, all 12 edges drawn, and the 8 triangular faces lightly shaded. Mark the midpoint M of edge from (3,0,0) to (0,3,0) and the distance from M to the origin.",
        "dimension": "coordinate_3d",
        "topic": "polyhedra",
    },
    {
        "id": "coord_45",
        "name": "Parallelepiped from Vectors",
        "text": "Three vectors a = (3, 0, 0), b = (1, 4, 0), c = (1, 1, 5) define a parallelepiped with one vertex at the origin O. Find the coordinates of all 8 vertices. Compute the volume using the scalar triple product. Sketch the parallelepiped in 3D with all vertices labeled, edges drawn, and the three base vectors a, b, c shown as arrows from O.",
        "dimension": "coordinate_3d",
        "topic": "polyhedra",
    },
]

# ======================================================================
# Combined lists
# ======================================================================

COORDINATE_ALL_2D = COORDINATE_QUESTIONS_2D_ORIGINAL + COORDINATE_QUESTIONS_2D_ADVANCED
COORDINATE_ALL_3D = COORDINATE_QUESTIONS_3D
COORDINATE_TEST_QUESTIONS = COORDINATE_ALL_2D + COORDINATE_ALL_3D

# ======================================================================
# Helper functions
# ======================================================================

def get_questions_by_dimension(dimension):
    # type: (str) -> list
    """Filter questions by dimension.

    Args:
        dimension: '2d', '3d', or 'all'.

    Returns:
        List of question dicts matching the dimension.
    """
    if dimension == "2d":
        return COORDINATE_ALL_2D
    elif dimension == "3d":
        return COORDINATE_ALL_3D
    return COORDINATE_TEST_QUESTIONS


def get_questions_by_topic(topic):
    # type: (str) -> list
    """Filter questions by topic.

    Args:
        topic: One of the topic strings, or 'all'.

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
    print(f"  2D: {len(COORDINATE_ALL_2D)}  (original: {len(COORDINATE_QUESTIONS_2D_ORIGINAL)}, advanced: {len(COORDINATE_QUESTIONS_2D_ADVANCED)})")
    print(f"  3D: {len(COORDINATE_ALL_3D)}")
    print()

    topics = {}
    for q in COORDINATE_TEST_QUESTIONS:
        topic = q["topic"]
        if topic not in topics:
            topics[topic] = []
        topics[topic].append(q)

    for topic, questions in sorted(topics.items()):
        dims = set(q["dimension"] for q in questions)
        dim_label = "/".join(sorted(dims))
        print(f"\n{topic.replace('_', ' ').title()} ({len(questions)} questions, {dim_label}):")
        for q in questions:
            print(f"  - {q['id']}: {q['name']}")
