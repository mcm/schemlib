import unittest
from dataclasses import dataclass
from typing import Optional

from bitstring import BitStream
from parameterized import parameterized_class, parameterized
from pydantic import BaseModel, ConfigDict, create_model

from schemlib import nbt


nbt_tag_tests = [
    (nbt.Byte(1), "Byte(1)", b"\x01"),
    (nbt.Short(1), "Short(1)", b"\x00\x01"),
    (nbt.Int(1), "Int(1)", b"\x00\x00\x00\x01"),
    (nbt.Long(1), "Long(1)", b"\x00\x00\x00\x00\x00\x00\x00\x01"),
    (nbt.Float(1.0), "Float(1.0)", b"?\x80\x00\x00"),
    (nbt.Double(1.0), "Double(1.0)", b"?\xf0\x00\x00\x00\x00\x00\x00"),
    (nbt.String("foo"), "String('foo')", b"\x00\x03foo"),
    (nbt.ByteArray([1, 2, 3]), "ByteArray([1, 2, 3])", b"\x00\x00\x00\x03\x01\x02\x03"),
    (nbt.IntArray([1, 2, 3]), "IntArray([1, 2, 3])", b"\x00\x00\x00\x03\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03"),
    (nbt.LongArray([1, 2, 3]), "LongArray([1, 2, 3])", b"\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x03"),
    (nbt.List([]), "List([])", b"\x00\x00\x00\x00\x00"),
    (nbt.List([nbt.Int(1), nbt.Int(2), nbt.Int(3)]), "List([Int(1), Int(2), Int(3)])", b"\x03\x00\x00\x00\x03\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03"),
    (nbt.Compound({"foo": nbt.String("bar")}), "Compound({'foo': String('bar')})", b"\x08\x00\x03foo\x00\x03bar\x00"),
    (nbt.Named({"": nbt.Compound({"foo":  nbt.String("bar")})}), "Named({'': Compound({'foo': String('bar')})})", b"\x0a\x00\x00\x08\x00\x03foo\x00\x03bar\x00"),
]


class TestSchemlib(unittest.TestCase):
    def test_list_from_buff_with_invalid_item_type(self):
        with self.assertRaises(ValueError):
            nbt.List.from_bytes(b"\xa3\x00\x00\x00\x03\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00\x03")
            
    def test_compound_from_buff_with_invalid_item_type(self):
        with self.assertRaises(ValueError):
            nbt.Compound.from_bytes(b"\x0a\x00\x00\xa3\x00\x03foo")
            
    def test_named_tag_only_one_key(self):
        with self.assertRaises(ValueError):
            nbt.Named({"foo": 1, "bar": 2})
            
    def test_model_to_compound_with_name(self):
        class Foo(BaseModel):
            bizz: str
            
        instance = Foo(bizz="buzz")
        nbt.model_to_compound(instance, name="bar")
        
    def test_load_nbt_from_bytes(self):
        self.assertEqual(nbt.load_nbt_from_bytes(b"\x0a\x00\x00\x08\x00\x03foo\x00\x03bar\x00"), nbt.Named({
            "": nbt.Compound({
                "foo": nbt.String("bar")
            })
        }))
        
    def test_load_nbt_from_bytes_as_model(self):
        class Foo(BaseModel):
            foo: nbt.String
            
        self.assertEqual(nbt.load_nbt_from_bytes(b"\x0a\x00\x00\x08\x00\x03foo\x00\x03bar\x00", Foo), Foo(foo="bar"))
        
    def test_load_nbt_from_file(self):
        named = nbt.load_nbt_from_file("tests/schematics/one_stone_block.litematic")
        self.assertEqual(named["Metadata"]["Name"], nbt.String("One Stone Block"))
        
    def test_model_extra_preserves_nbt_info(self):
        class Foo(BaseModel):
            model_config = ConfigDict(extra="allow")
            
        Foo.model_validate(
            nbt.Named({"": nbt.Compound({
                "foo": nbt.String,
            })})
        )
        
        
tag_type_ids = {
    1: nbt.Byte,
    2: nbt.Short,
    3: nbt.Int,
    4: nbt.Long,
    5: nbt.Float,
    6: nbt.Double,
    7: nbt.ByteArray,
    8: nbt.String,
    9: nbt.List,
    10: nbt.Compound,
    11: nbt.IntArray,
    12: nbt.LongArray,
}
        
        
class TestNbtTagTypeRegistry(unittest.TestCase):
    @parameterized.expand(tag_type_ids.items())
    def test_known_tag_types(self, tag_type_id: int, tag_type: type[nbt.NbtTag]):
        self.assertEqual(nbt.tag_type_registry[tag_type_id], tag_type)
        self.assertEqual(tag_type.tag_type_id, tag_type_id)
        
    def test_overwriting_tag_type_raises_key_error(self):
        with self.assertRaises(KeyError):
            nbt.register_tag_type(1, nbt.Int)
        
    def test_register_tag_type_with_invalid_type_raises_type_error(self):
        with self.assertRaises(TypeError):
            nbt.register_tag_type(1, set)  # type: ignore
            
    def test_no_base_class_implementation_from_buff(self):
        class Foo(nbt.NbtTag): ...
        
        with self.assertRaises(NotImplementedError):
            Foo.from_buff(BitStream())
            
    def test_no_base_class_implementation_to_bytes(self):
        class Foo(nbt.NbtTag.nbt_tag_class_factory(str)): ...
        
        with self.assertRaises(NotImplementedError):
            Foo("foo").to_bytes()
            
    @parameterized.expand(nbt_tag_tests)
    def test_nbt_tag_repr(self, tag_value: nbt.AnyNBT, expected_repr: str, _):
        self.assertEqual(repr(tag_value), expected_repr)
            
    @parameterized.expand(nbt_tag_tests)
    def test_nbt_tag_from_bytes(self, tag_value: nbt.AnyNBT, _, bytes_value: bytes):
        self.assertEqual(type(tag_value).from_bytes(bytes_value), tag_value)
            
    @parameterized.expand(nbt_tag_tests)
    def test_nbt_tag_to_bytes(self, tag_value: nbt.AnyNBT, _, bytes_value: bytes):
        self.assertEqual(tag_value.to_bytes(), bytes_value)