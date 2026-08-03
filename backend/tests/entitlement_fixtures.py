from datetime import date

from app.entitlement_service import CAPABILITIES
from app.models_school import SchoolEntitlement


def grant_capabilities(db, school, actor, *capabilities: str) -> None:
    required: set[str] = set()

    def include(capability: str) -> None:
        if capability in required:
            return
        required.add(capability)
        for dependency in CAPABILITIES[capability].dependencies:
            include(dependency)

    for capability in capabilities:
        include(capability)
    existing = {
        row[0]
        for row in db.query(SchoolEntitlement.capability)
        .filter(
            SchoolEntitlement.school_id == school.id,
            SchoolEntitlement.capability.in_(required),
        )
        .all()
    }
    db.add_all(
        SchoolEntitlement(
            school_id=school.id,
            capability=capability,
            enabled=True,
            source="pilot",
            effective_from=date.today(),
            updated_by_user_id=actor.id,
        )
        for capability in required - existing
    )


def grant_all_capabilities(db, school, actor) -> None:
    grant_capabilities(db, school, actor, *CAPABILITIES)
