"""Pure decision rules for friend-support slot recognition."""


def is_occupied_support_slot(standard_deviation, edge_density):
    """Return whether a support slot contains a detailed monster card."""
    return standard_deviation >= 18.0 and edge_density >= 0.08
