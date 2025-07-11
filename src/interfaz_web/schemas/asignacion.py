# src/interfaz_web/schemas/asignacion.py
from typing import List

from pydantic import BaseModel


class AssignmentUpdateRequest(BaseModel):
    assign_team_ids: List[int]
    unassign_team_ids: List[int]
