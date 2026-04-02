"""GraphQL app — mounts Strawberry at /graphql."""

from __future__ import annotations

import strawberry
from strawberry.fastapi import GraphQLRouter

from .schema import schema

graphql_router = GraphQLRouter(schema, graphiql=True)
