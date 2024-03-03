from sqlalchemy.orm import as_declarative, declared_attr


@as_declarative()
class Base:
    id: int
    __name__: str

    @declared_attr.directive
    def __tablename__(cls) -> str: # noqa
        return cls.__name__.lower()
