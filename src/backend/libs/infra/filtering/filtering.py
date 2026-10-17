"""Turns an OData `$filter` string, such as `display_name eq 'Avi'`, into a SQL condition.

A filter schema names the paths a caller may filter on and the SQL expression behind each:
a column, a renamed column, a joined column, or a computed expression. Every filter is checked
before it runs: its syntax, its paths, and the type of every value it compares.
"""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from odata_query import ast, exceptions
from odata_query.grammar import ODataLexer, ODataParser
from odata_query.sqlalchemy.core import AstToSqlAlchemyCoreVisitor
from sqlalchemy import BindParameter, ColumnElement, TypeDecorator, Uuid, literal
from sqlalchemy.orm import Mapped, QueryableAttribute
from sqlalchemy.types import TypeEngine

SUPPORTED_FUNCTIONS = frozenset({"contains", "startswith", "endswith"})
# The syntax the filtering skill teaches; anything else is rejected before it reaches the database.
SUPPORTED_NODES = (
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Call,
    ast.Identifier,
    ast.Attribute,
    ast.List,
    ast.Null,
    ast.String,
    ast.Integer,
    ast.Float,
    ast.Boolean,
    ast.Date,
    ast.DateTime,
    ast.GUID,
)
LITERAL_TYPES: Mapping[type, type] = {
    ast.String: str,
    ast.Integer: int,
    ast.Float: float,
    ast.Boolean: bool,
    ast.Date: date,
    ast.DateTime: datetime,
    ast.GUID: UUID,
}
TYPE_NAMES: Mapping[type, str] = {
    str: "text",
    int: "whole numbers",
    float: "numbers",
    Decimal: "numbers",
    bool: "true or false",
    date: "dates",
    datetime: "date-times",
    UUID: "IDs",
}
# A field that holds numbers with a fraction also accepts whole numbers.
ACCEPTS: Mapping[type, frozenset[type]] = {
    float: frozenset({float, int}),
    Decimal: frozenset({float, int}),
}


class InvalidFilterError(Exception):
    """The filter is not valid. The message says why; `valid_paths` lists what can be filtered."""

    def __init__(self, problem: str, valid_paths: list[str]) -> None:
        super().__init__(problem)
        self.valid_paths = valid_paths


class FilterSchema:
    def __init__(self, fields: Mapping[str, ColumnElement[Any] | Mapped[Any]]) -> None:
        self._fields = {path: _sql(e) for path, e in fields.items()}
        # Read once, so a field whose type has no Python equivalent fails when the module loads.
        self._types = {path: _python_type(e.type) for path, e in self._fields.items()}

    @property
    def paths(self) -> list[str]:
        return sorted(self._fields)

    def where(self, filter: str) -> ColumnElement[bool]:
        """Returns the SQL condition for the filter, or raises InvalidFilterError."""
        try:
            tree = _parse(filter)
        except exceptions.ODataSyntaxError:
            raise self.invalid("not a valid filter") from None
        return _ToSql(self).visit(tree)

    def expression(self, path: str) -> ColumnElement[Any]:
        if path not in self._fields:
            raise self.invalid(f"unknown field '{path}'")
        return self._fields[path]

    def type_of(self, path: str) -> type:
        self.expression(path)  # Rejects an unknown path before its type is read.
        return self._types[path]

    def invalid(self, problem: str) -> InvalidFilterError:
        return InvalidFilterError(problem, self.paths)


def _parse(filter: str) -> Any:
    # odata-query's lexer and parser come from `sly`, which has no type information.
    return ODataParser().parse(ODataLexer().tokenize(filter))  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]


class _ToSql(AstToSqlAlchemyCoreVisitor):
    """odata-query's SQL visitor, with fields resolved through the schema and checked by type."""

    def __init__(self, schema: FilterSchema) -> None:
        self._schema = schema

    def visit(self, node: Any) -> Any:
        if not isinstance(node, SUPPORTED_NODES):
            what = "arithmetic" if isinstance(node, ast.BinOp) else f"'{type(node).__name__}'"
            raise self._schema.invalid(f"{what} is not supported")
        return super().visit(node)

    def visit_Identifier(self, node: ast.Identifier) -> Any:
        return self._schema.expression(node.full_name())

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        return self._schema.expression(_path(node))

    def visit_GUID(self, node: ast.GUID) -> BindParameter[UUID]:
        # odata-query binds IDs as text, which Postgres will not compare with a uuid column.
        return literal(UUID(node.val), Uuid())

    def visit_Call(self, node: ast.Call) -> Any:
        name = node.func.full_name()
        if name not in SUPPORTED_FUNCTIONS:
            raise self._schema.invalid(f"{name} is not supported")
        field = node.args[0] if node.args else None
        if (
            not isinstance(field, ast.Identifier | ast.Attribute)
            or self._field_type(field) is not str
        ):
            raise self._schema.invalid(f"{name} needs a text field")
        return super().visit_Call(node)

    def visit_Compare(self, node: ast.Compare) -> Any:
        condition = self.visit(node.comparator)(self.visit(node.left), self.visit(node.right))
        values = node.right.val if isinstance(node.right, ast.List) else [node.right]
        if isinstance(node.left, ast.Identifier | ast.Attribute):
            for value in values:
                self._check(node.left, value)
        elif isinstance(node.right, ast.Identifier | ast.Attribute):
            self._check(node.right, node.left)
        else:
            raise self._schema.invalid(
                "compare a field with a value, such as display_name eq 'Avi'"
            )
        return condition

    def _check(self, field: ast.Identifier | ast.Attribute, value: object) -> None:
        """Checks that the value fits the field's type. Null fits every field."""
        field_type = self._field_type(field)
        if isinstance(value, ast.Identifier | ast.Attribute):
            if self._field_type(value) is not field_type:
                raise self._schema.invalid(
                    f"'{_path(field)}' and '{_path(value)}' hold different types"
                )
            return
        value_type = LITERAL_TYPES.get(type(value))
        if value_type is None:
            return
        if value_type not in ACCEPTS.get(field_type, frozenset({field_type})):
            raise self._schema.invalid(f"'{_path(field)}' holds {TYPE_NAMES[field_type]}")

    def _field_type(self, field: ast.Identifier | ast.Attribute) -> type:
        return self._schema.type_of(_path(field))


def _sql(field: ColumnElement[Any] | Mapped[Any]) -> ColumnElement[Any]:
    """The SQL expression behind a field: a column or expression as it is, or a table model's
    attribute, such as `col(ClientRow.email)`, as its column."""
    if isinstance(field, QueryableAttribute):
        return field.expression
    assert isinstance(field, ColumnElement)
    return field


def _python_type(sql_type: TypeEngine[Any]) -> type:
    """The Python type a column holds. A wrapper type, such as SQLModel's string type, reports
    `object`, so the type it wraps is read instead."""
    if isinstance(sql_type, TypeDecorator):
        return _python_type(sql_type.impl_instance)
    return sql_type.python_type


def _path(field: ast.Identifier | ast.Attribute) -> str:
    """The field's path as the API spells it, such as `company/name`."""
    if isinstance(field, ast.Identifier):
        return field.full_name()
    assert isinstance(field.owner, ast.Identifier | ast.Attribute)
    return f"{_path(field.owner)}/{field.attr}"
