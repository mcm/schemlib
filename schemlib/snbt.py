import json
from typing import Any, cast

import pyparsing as pp
from pyparsing import pyparsing_common as ppc

from schemlib import nbt


Compound = pp.Forward()
SnbtValue = pp.Forward()

SnbtElements = pp.delimited_list(SnbtValue)

FloatingPointNumber = pp.Combine(pp.Word(pp.nums) + "." + pp.Word(pp.nums)).set_parse_action(lambda toks: float(cast(str, toks[0])))

Byte = (ppc.signed_integer() + pp.Suppress(pp.CaselessLiteral("B"))).add_parse_action(lambda toks: (nbt.Byte, toks[0]))
Short = (ppc.signed_integer() + pp.Suppress(pp.CaselessLiteral("S"))).add_parse_action(lambda toks: (nbt.Short, toks[0]))
Int = ppc.signed_integer().add_parse_action(lambda toks: (nbt.Int, toks[0]))
Long = (ppc.signed_integer() + pp.Suppress(pp.CaselessLiteral("L"))).add_parse_action(lambda toks: (nbt.Long, toks[0]))
Float = (ppc.fnumber + pp.Suppress(pp.CaselessLiteral("F"))).add_parse_action(lambda toks: (nbt.Float, toks[0]))
Double = ((ppc.fnumber() + pp.Suppress(pp.CaselessLiteral("D"))) | FloatingPointNumber).add_parse_action(lambda toks: (nbt.Double, toks[0]))
# String = pp.quoted_string().add_parse_action(pp.remove_quotes).add_parse_action(lambda toks: (nbt.String, toks[0]))
String = pp.quoted_string().add_parse_action(lambda toks: (nbt.String, json.loads(cast(str, toks[0]))))

ByteArray = pp.Group(pp.Suppress("[B;") + pp.Optional(pp.DelimitedList(Byte)) + pp.Suppress("]"), aslist=True).add_parse_action(
    lambda toks: (nbt.ByteArray, [x[1] for x in toks[0]])
)
IntArray = pp.Group(pp.Suppress("[I;") + pp.Optional(pp.DelimitedList(Int)) + pp.Suppress("]"), aslist=True).add_parse_action(
    lambda toks: (nbt.IntArray, [x[1] for x in toks[0]])
)
LongArray = pp.Group(pp.Suppress("[L;") + pp.Optional(pp.DelimitedList(Long)) + pp.Suppress("]"), aslist=True).add_parse_action(
    lambda toks: (nbt.LongArray, [x[1] for x in toks[0]])
)

List = pp.Group(pp.Suppress("[") + pp.Optional(SnbtElements) + pp.Suppress("]"), aslist=True).add_parse_action(lambda toks: (nbt.List, toks[0]))

SnbtValue << (Byte | Short | Long | Float | Double | Int | String | ByteArray | IntArray | LongArray | List | Compound)

CompoundKey = pp.Word(pp.alphanums + "_-.+") | pp.quoted_string().add_parse_action(pp.remove_quotes)
CompoundValues = pp.DelimitedList(pp.Group(CompoundKey + pp.Suppress(":") + SnbtValue, aslist=True))

Compound << pp.Group(pp.Suppress("{") + pp.Optional(CompoundValues) + pp.Suppress("}"), aslist=True).add_parse_action(
    lambda toks: (nbt.Compound, toks[0])
)


def make_tag[T: nbt.AnyNBT](tag_type: type[T], value: Any) -> T:
    if tag_type is nbt.List:
        return tag_type([make_tag(item_tag_type, item_tag_value) for (item_tag_type, item_tag_value) in value])
    if tag_type is nbt.Compound:
        return tag_type({k: make_tag(item_tag_type, item_tag_value) for (k, (item_tag_type, item_tag_value)) in value})
    return tag_type(value)


def from_snbt(v: str):
    tag_type, value = SnbtValue.parse_string(v)[0]
    return make_tag(tag_type, value)


def to_snbt(v: "nbt.AnyNBT") -> str:
    if isinstance(v, nbt.Byte):
        return f"{v.to_obj()}B"
    if isinstance(v, nbt.Short):
        return f"{v.to_obj()}S"
    if isinstance(v, nbt.Int):
        return f"{v.to_obj()}"
    if isinstance(v, nbt.Long):
        return f"{v.to_obj()}L"
    if isinstance(v, nbt.Float):
        return f"{v.to_obj()}F"
    if isinstance(v, nbt.Double):
        return f"{v.to_obj()}D"
    if isinstance(v, nbt.String):
        return json.dumps(v)
    if isinstance(v, nbt.List):
        values = [to_snbt(x) for x in v]
        return f"[{','.join(values)}]"
    if isinstance(v, nbt.ByteArray | nbt.IntArray | nbt.LongArray):
        unit = {
            8: "B",
            32: "I",
            64: "L",
        }[v.width.bitlength]

        values = [str(x) if isinstance(v, nbt.IntArray) else f"{x}{unit}" for x in v]
        return f"[{unit};{','.join(values)}]"
    if isinstance(v, nbt.Compound):
        def key_to_snbt(key):
            if any(c not in pp.alphanums + "_-.+" for c in key):
                return json.dumps(key)
            return key
        
        values = [f"{key_to_snbt(key)}:{to_snbt(val)}" for (key, val) in v.items()]
        return "{" + ",".join(values) + "}"
    raise TypeError(type(v), v)  # pragma: nocover