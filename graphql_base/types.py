# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo import fields


def odoo_attr_resolver(attname, default_value, root, info, **args):
    """An attr resolver that is specialized for Odoo recordsets.

    It converts False to None, except for Odoo Boolean fields.
    This is necessary because Odoo null values are often represented
    as False, and graphene would convert a String field with value False
    to "false".

    It converts datetimes to the user timezone.

    It also raises an error if the attribute is not present, ignoring
    any default value, so as to return if the schema declares a field
    that is not present in the underlying Odoo model.
    """
    value = getattr(root, attname)
    field = root._fields.get(attname)
    if value is False:
        if not isinstance(field, fields.Boolean):
            return None
    elif isinstance(field, fields.Date):
        return fields.Date.from_string(value)
    elif isinstance(field, fields.Datetime):
        return fields.Datetime.context_timestamp(root, fields.Datetime.from_string(value))
    elif isinstance(field, fields.Binary):
        return value.decode()
    return value


class OdooObjectType(graphene.ObjectType):
    """A graphene ObjectType with an Odoo aware default resolver."""

    @classmethod
    def __init_subclass_with_meta__(cls, default_resolver=None, **options):
        if default_resolver is None:
            default_resolver = odoo_attr_resolver

        return super(OdooObjectType, cls).__init_subclass_with_meta__(
            default_resolver=default_resolver, **options
        )


class JSON(graphene.Scalar):
    """
    The `JSON` scalar type represents JSON values as specified by
    [ECMA-404](http://www.ecma-international.org/
    publications/files/ECMA-ST/ECMA-404.pdf).
    """

    @staticmethod
    def identity(value):
        if isinstance(value, (str, bool, int, float)):
            return value.__class__(value)
        elif isinstance(value, (list, dict)):
            return value
        else:
            return None

    serialize = identity
    parse_value = identity

    @staticmethod
    def parse_literal(ast):
        if isinstance(ast, (StringValue, BooleanValue)):
            return ast.value
        elif isinstance(ast, IntValue):
            return int(ast.value)
        elif isinstance(ast, FloatValue):
            return float(ast.value)
        elif isinstance(ast, ListValue):
            return [JSON.parse_literal(value) for value in ast.values]
        elif isinstance(ast, ObjectValue):
            return {field.name.value: JSON.parse_literal(field.value) for field in ast.fields}
        else:
            return None
