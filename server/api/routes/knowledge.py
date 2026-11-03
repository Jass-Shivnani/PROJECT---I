"""
Dione AI — Knowledge Graph Routes

REST endpoints for querying and managing the knowledge graph.
"""

from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from loguru import logger

from server.knowledge.entities import Entity, EntityType
from server.knowledge.relations import Relation, RelationType

router = APIRouter()


class EntityRequest(BaseModel):
    entity_type: str = "concept"
    name: str
    properties: dict = {}


class RelationRequest(BaseModel):
    source_id: str
    target_id: str
    relation_type: str = "related_to"
    weight: float = 1.0
    context: str = ""


class QueryRequest(BaseModel):
    query: str
    max_results: int = 10


@router.get("/entities")
async def list_entities(request: Request, entity_type: Optional[str] = None):
    """List all entities in the knowledge graph."""
    kg = request.app.state.knowledge
    if entity_type:
        entities = kg.get_entities_by_type(entity_type)
    else:
        entities = []
        for node_id, data in kg.graph.nodes(data=True):
            entities.append({"id": node_id, **data})
    return {"entities": entities, "total": len(entities)}


@router.post("/entities")
async def add_entity(req: EntityRequest, request: Request):
    """Add an entity to the knowledge graph."""
    kg = request.app.state.knowledge
    try:
        etype = EntityType(req.entity_type.lower())
    except ValueError:
        etype = EntityType.CONCEPT
    entity = Entity(id="", name=req.name, type=etype, metadata=req.properties or {})
    entity_id = kg.add_entity(entity)
    kg.save()
    return {"id": entity_id, "status": "created"}


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str, request: Request):
    """Get a specific entity and its connections."""
    kg = request.app.state.knowledge
    entity = kg.get_entity(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    connections = kg.get_connections(entity_id)
    return {
        "entity": entity,
        "connections": connections,
    }


@router.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str, request: Request):
    """Remove an entity from the knowledge graph."""
    kg = request.app.state.knowledge
    kg.remove_entity(entity_id)
    kg.save()
    return {"status": "deleted"}


@router.post("/relations")
async def add_relation(req: RelationRequest, request: Request):
    """Add a relation between two entities."""
    kg = request.app.state.knowledge
    try:
        rtype = RelationType(req.relation_type.lower())
    except ValueError:
        rtype = RelationType.RELATED_TO
    rel = Relation(
        id="",
        source_id=req.source_id,
        target_id=req.target_id,
        relation_type=rtype,
        weight=req.weight,
        metadata={"context": req.context} if req.context else {},
    )
    kg.add_relation(rel)
    kg.save()
    return {"status": "created"}


@router.post("/query")
async def query_knowledge(req: QueryRequest, request: Request):
    """Query the knowledge graph with natural language."""
    kg = request.app.state.knowledge
    results = await kg.query_relevant(req.query, max_results=req.max_results)
    return {"results": results, "total": len(results) if isinstance(results, list) else (1 if results else 0)}


@router.get("/stats")
async def knowledge_stats(request: Request):
    """Get knowledge graph statistics."""
    kg = request.app.state.knowledge
    return kg.get_stats()
