import unittest
from typing import Any, Optional

from parameterized import parameterized_class
from pydantic import BaseModel
from pyparsing import ParserElement

from schemlib import nbt, snbt

test_snbt_tag_values = [
    { "name": "snbt_byte_1", "snbt_type": snbt.Byte, "snbt_value": "34B", "parsed_value": (nbt.Byte, 34), "tag_value": nbt.Byte(34)},
    { "name": "snbt_byte_2", "snbt_type": snbt.Byte, "snbt_value": "-20B", "parsed_value": (nbt.Byte, -20), "tag_value": nbt.Byte(-20)},
    { "name": "snbt_short_1", "snbt_type": snbt.Short, "snbt_value": "31415S", "parsed_value": (nbt.Short, 31415), "tag_value": nbt.Short(31415)},
    { "name": "snbt_short_2", "snbt_type": snbt.Short, "snbt_value": "-27183S", "parsed_value": (nbt.Short, -27183), "tag_value": nbt.Short(-27183)},
    { "name": "snbt_integer", "snbt_type": snbt.Int, "snbt_value": "31415926", "parsed_value": (nbt.Int, 31415926), "tag_value": nbt.Int(31415926)},
    { "name": "snbt_long", "snbt_type": snbt.Long, "snbt_value": "31415926L", "parsed_value": (nbt.Long, 31415926), "tag_value": nbt.Long(31415926)},
    { "name": "snbt_float", "snbt_type": snbt.Float, "snbt_value": "3.1415926F", "parsed_value": (nbt.Float, 3.1415926), "tag_value": nbt.Float(3.1415926)},
    { "name": "snbt_double", "snbt_type": snbt.Double, "snbt_value": "3.1415926", "parsed_value": (nbt.Double, 3.1415926), "tag_value": nbt.Double(3.1415926),
      "serialized_value": "3.1415926D"},
    { "name": "snbt_string_1", "snbt_type": snbt.String, "snbt_value": r'"Call me \"Ishmael\""', "parsed_value": (nbt.String, r'Call me "Ishmael"'),
      "tag_value": nbt.String(r'Call me "Ishmael"')},
    { "name": "snbt_string_2", "snbt_type": snbt.String, "snbt_value": '''"Call me 'Ishmael'"''', "parsed_value": (nbt.String, "Call me 'Ishmael'"),
      "tag_value": nbt.String("Call me 'Ishmael'")},
    # (snbt.String, r"""'Call me "Ishmael"'""", nbt.TagString(r'Call me "Ishmael"')),
    # (snbt.String, r"""'Call me \'Ishmael\''""", nbt.TagString(r'Call me \'Ishmael\'')),
    { "name": "snbt_list", "snbt_type": snbt.List, "snbt_value": "[3.2D,64.5D,129.5D]",
      "parsed_value": (nbt.List, [(nbt.Double, 3.2), (nbt.Double, 64.5), (nbt.Double, 129.5)]),
      "tag_value": nbt.List([nbt.Double(3.2), nbt.Double(64.5), nbt.Double(129.5)])},
    {
        "name": "snbt_compound",
        "snbt_type": snbt.Compound,
        "snbt_value": "{X:3,Y:64,Z:129}",
        "parsed_value": (nbt.Compound, [["X", (nbt.Int, 3)], ["Y", (nbt.Int, 64)], ["Z", (nbt.Int, 129)]]),
        "tag_value": nbt.Compound({"X": nbt.Int(3), "Y": nbt.Int(64), "Z": nbt.Int(129)}),
    },
    {"name": "snbt_byte_array", "snbt_type": snbt.ByteArray, "snbt_value": "[B;1B,2B,3B]", "parsed_value": (nbt.ByteArray, [1, 2, 3]), "tag_value": nbt.ByteArray([1,2,3])},
    {"name": "snbt_int_array", "snbt_type": snbt.IntArray, "snbt_value": "[I;1,2,3]", "parsed_value": (nbt.IntArray, [1, 2, 3]), "tag_value": nbt.IntArray([1,2,3])},
    {"name": "snbt_long_array", "snbt_type": snbt.LongArray, "snbt_value": "[L;1L,2L,3L]", "parsed_value": (nbt.LongArray, [1, 2, 3]), "tag_value": nbt.LongArray([1,2,3])},
]


@parameterized_class(test_snbt_tag_values)
class TestSchemlibSnbtTags(unittest.TestCase):
    name: str
    snbt_type: ParserElement
    snbt_value: str
    parsed_value: tuple[type[nbt.AnyNBT], Any]
    tag_value: nbt.AnyNBT
    serialized_value: Optional[str] = None
    
    def test_parse_snbt(self):
        value = self.snbt_type.parse_string(self.snbt_value)[0]
        self.assertEqual(value, self.parsed_value)
        
        value = snbt.from_snbt(self.snbt_value)
        self.assertEqual(value, self.tag_value)

    def test_serialize_snbt(self):
        value = snbt.to_snbt(self.tag_value)
        self.assertEqual(value, self.serialized_value or self.snbt_value)
        
        
test_snbt_string_values = [
    {
        "snbt_str": '{Pos:[1d,2d,3d],Tags:["a","b"]}',
        "tag_value": nbt.Compound({
            "Pos": nbt.List([nbt.Double(1.0), nbt.Double(2.0), nbt.Double(3.0)]),
            "Tags": nbt.List([nbt.String("a"), nbt.String("b")]),
        }),
        "serialized_value": '{Pos:[1.0D,2.0D,3.0D],Tags:["a","b"]}'
    }
]


@parameterized_class(test_snbt_string_values)
class TestSchemlibSnbtStrings(unittest.TestCase):
    snbt_str: str
    tag_value: nbt.AnyNBT
    serialized_value: Optional[str] = None
    
    def test_snbt_serialize(self):
        self.assertEqual(snbt.to_snbt(self.tag_value), self.serialized_value or self.snbt_str)
        
    def test_snbt_deserialize(self):
        self.assertEqual(snbt.from_snbt(self.snbt_str), self.tag_value)