"""Analyze portfolio data for scale and efficiency metrics."""
from app.models.input_data import Property, ClientInfo
from app.models.analysis import PortfolioMetrics


def analyze_portfolio(
    properties: list[Property],
    client_info: ClientInfo,
) -> PortfolioMetrics:
    """Compute portfolio-level metrics.

    Uses client_info for door count and staff count (authoritative),
    and supplements with property-level data where available.
    """
    total_doors = client_info.door_count
    total_properties = client_info.property_count

    # If we have property data, use it for units-per-property
    if properties:
        total_from_props = sum(p.unit_count for p in properties)
        avg_units = total_from_props / len(properties) if properties else 0
    else:
        avg_units = total_doors / max(1, total_properties)

    doors_per_staff = total_doors / max(1, client_info.staff_count)

    return PortfolioMetrics(
        total_doors=total_doors,
        total_properties=total_properties,
        avg_units_per_property=round(avg_units, 1),
        doors_per_staff=round(doors_per_staff, 1),
    )
