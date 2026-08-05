from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.session import get_db
from app.models.employee import Employee
from app.services.auth import get_current_user

router = APIRouter()


def _build_tree(nodes: dict[int, dict], children_map: dict[int | None, list[int]], parent_id: int | None = None):
    result = []
    for node_id in children_map.get(parent_id, []):
        node = nodes[node_id]
        result.append(
            {
                "id": node["id"],
                "name": node["name"],
                "role": node["role"],
                "manager_id": node["manager_id"],
                "children": _build_tree(nodes, children_map, node_id),
            }
        )
    return result


@router.get("/tree")
async def org_tree(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    rows = (await db.execute(select(Employee).order_by(Employee.id.asc()))).scalars().all()

    nodes: dict[int, dict] = {}
    children_map: dict[int | None, list[int]] = defaultdict(list)
    for row in rows:
        nodes[row.id] = {
            "id": row.id,
            "name": row.name,
            "role": row.role.value,
            "manager_id": row.manager_id,
        }
        children_map[row.manager_id].append(row.id)

    tree = _build_tree(nodes, children_map, None)
    return success_response({"items": tree})
