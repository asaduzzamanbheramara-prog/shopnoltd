import strawberry
from fastapi import APIRouter
from strawberry.fastapi import GraphQLRouter


@strawberry.type
class Service:
    name: str
    status: str


@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Welcome to Shopnoltd GraphQL"

    @strawberry.field
    async def services(self) -> list[Service]:
        from app.services.services import health

        h = await health()
        return [Service(name=n, status=s) for n, s in h.items()]


schema = strawberry.Schema(query=Query)
router = APIRouter()
router.include_router(GraphQLRouter(schema), prefix="")
