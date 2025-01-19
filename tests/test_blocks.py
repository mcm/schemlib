import re
import unittest

import fauxfactory
import pytest
from amulet_nbt import StringTag
from parameterized import parameterized
from PyMCTranslate import new_translation_manager
from PyMCTranslate.py3.api import amulet_objects

from schemlib import blocks, nbt


tm = new_translation_manager()
MINECRAFT_1_12 = tm.get_version("java", (1, 12, 2))
MINECRAFT_1_20 = tm.get_version("java", (1, 20, 1))


class TestSchemlibBlock(unittest.TestCase):
    def test_block_name_is_blockstate_name(self):
        block_name = fauxfactory.gen_alpha()
        block = blocks.Block(pos=blocks.BlockPos(x=0, y=0, z=0), state=blocks.BlockState(Name=block_name))
        self.assertEqual(block.name, block_name)

    # def test_block_from_1_12_to_1_20(self):
    #     block_1_12 = blocks.Block(
    #         pos=blocks.BlockPos.ORIGIN,
    #         state=blocks.BlockState(
    #             Name="minecraft:stone_slab",
    #             Properties={"variant": "stone"}
    #         )
    #     )
        
    #     block_1_20 = blocks.Block(
    #         pos=blocks.BlockPos.ORIGIN,
    #         state=blocks.BlockState(
    #             Name="minecraft:smooth_stone_slab",
    #             Properties={"type": "bottom"}
    #         )
    #     )
        
    #     self.assertEqual(block_1_12.to_version(MINECRAFT_1_12, MINECRAFT_1_20), block_1_20)
        
    # def test_block_from_1_20_to_1_12(self):
    #     block_1_12 = blocks.Block(
    #         pos=blocks.BlockPos.ORIGIN,
    #         state=blocks.BlockState(
    #             Name="minecraft:stone_slab",
    #             Properties={"variant": "stone", "half": "bottom"}
    #         )
    #     )
        
    #     block_1_20 = blocks.Block(
    #         pos=blocks.BlockPos.ORIGIN,
    #         state=blocks.BlockState(
    #             Name="minecraft:smooth_stone_slab",
    #             Properties={"type": "bottom"}
    #         )
    #     )
        
    #     self.assertEqual(block_1_20.to_version(MINECRAFT_1_20, MINECRAFT_1_12), block_1_12)


class SchemlibTestBlockPos(unittest.TestCase):
    def test_blockpos_origin(self):
        self.assertEqual(blocks.BlockPos.ORIGIN, blocks.BlockPos(x=0, y=0, z=0))
        
    def test_blockpos_from_tuple(self):
        self.assertEqual(
            blocks.BlockPos.model_validate((0, 0, 0)),
            blocks.BlockPos(x=0, y=0, z=0)
        )

    def test_blockpos_add_blockpos(self):
        p1 = blocks.BlockPos(
            x=fauxfactory.gen_integer(-128, 127),
            y=fauxfactory.gen_integer(-128, 127),
            z=fauxfactory.gen_integer(-128, 127),
        )

        p2 = blocks.BlockPos(
            x=fauxfactory.gen_integer(-128, 127),
            y=fauxfactory.gen_integer(-128, 127),
            z=fauxfactory.gen_integer(-128, 127),
        )

        expected_value = blocks.BlockPos(
            x=p1.x + p2.x,
            y=p1.y + p2.y,
            z=p1.z + p2.z,
        )

        self.assertEqual(p1 + p2, expected_value)

    def test_blockpos_add_tuple(self):
        p1 = blocks.BlockPos(
            x=fauxfactory.gen_integer(-128, 127),
            y=fauxfactory.gen_integer(-128, 127),
            z=fauxfactory.gen_integer(-128, 127),
        )

        p2 = (
            fauxfactory.gen_integer(-128, 127),
            fauxfactory.gen_integer(-128, 127),
            fauxfactory.gen_integer(-128, 127),
        )

        expected_value = blocks.BlockPos(
            x=p1.x + p2[0],
            y=p1.y + p2[1],
            z=p1.z + p2[2],
        )

        self.assertEqual(p1 + p2, expected_value)

    def test_blockpos_subtract_blockpos(self):
        p1 = blocks.BlockPos(
            x=fauxfactory.gen_integer(-128, 127),
            y=fauxfactory.gen_integer(-128, 127),
            z=fauxfactory.gen_integer(-128, 127),
        )

        p2 = blocks.BlockPos(
            x=fauxfactory.gen_integer(-128, 127),
            y=fauxfactory.gen_integer(-128, 127),
            z=fauxfactory.gen_integer(-128, 127),
        )

        expected_value = blocks.BlockPos(
            x=p1.x - p2.x,
            y=p1.y - p2.y,
            z=p1.z - p2.z,
        )

        self.assertEqual(p1 - p2, expected_value)

    def test_blockpos_subtract_tuple(self):
        p1 = blocks.BlockPos(
            x=fauxfactory.gen_integer(-128, 127),
            y=fauxfactory.gen_integer(-128, 127),
            z=fauxfactory.gen_integer(-128, 127),
        )

        p2 = (
            fauxfactory.gen_integer(-128, 127),
            fauxfactory.gen_integer(-128, 127),
            fauxfactory.gen_integer(-128, 127),
        )

        expected_value = blocks.BlockPos(
            x=p1.x - p2[0],
            y=p1.y - p2[1],
            z=p1.z - p2[2],
        )

        self.assertEqual(p1 - p2, expected_value)

    def test_blockpos_unpack(self):
        p1 = blocks.BlockPos(
            x=fauxfactory.gen_integer(-128, 127),
            y=fauxfactory.gen_integer(-128, 127),
            z=fauxfactory.gen_integer(-128, 127),
        )

        (x, y, z) = p1.astuple()

        self.assertEqual(x, p1.x)
        self.assertEqual(y, p1.y)
        self.assertEqual(z, p1.z)

    def test_blockpos_to_tuple(self):
        p1 = blocks.BlockPos(
            x=fauxfactory.gen_integer(-128, 127),
            y=fauxfactory.gen_integer(-128, 127),
            z=fauxfactory.gen_integer(-128, 127),
        )

        expected_value = (p1.x, p1.y, p1.z)

        self.assertEqual(p1.astuple(), expected_value)
        
    def test_blockpos_equals_tuple(self):
        p1 = (
            fauxfactory.gen_integer(-128, 127),
            fauxfactory.gen_integer(-128, 127),
            fauxfactory.gen_integer(-128, 127),
        )
        
        p2 = blocks.BlockPos(
            x=p1[0],
            y=p1[1],
            z=p1[2],
        )
        
        self.assertEqual(p1, p2)
        
    def test_blockpos_equals_specialzed_subclass(self):
        from schemlib import nbt
        
        class SpecialBlockPos(blocks.BlockPos[nbt.Int]): ...
        
        p1 = blocks.BlockPos(
            x=fauxfactory.gen_integer(-128, 127),
            y=fauxfactory.gen_integer(-128, 127),
            z=fauxfactory.gen_integer(-128, 127),
        )
        
        p2 = SpecialBlockPos(
            x=p1.x,
            y=p1.y,
            z=p1.z,
        )
        
        self.assertEqual(p1, p2)


blockstate_strings = [
    ("minecraft:air", blocks.BlockState(Name="minecraft:air")),
    ("minecraft:stone[]", blocks.BlockState(Name="minecraft:stone"), "minecraft:stone"),
    ('minecraft:oak_slab[type=top]', blocks.BlockState(Name="minecraft:oak_slab", Properties={"type": "top"})),
    (
        'minecraft:stone_stairs[half="bottom", facing="east"]',
        blocks.BlockState(Name="minecraft:stone_stairs", Properties={"half": "bottom", "facing": "east"}),
        'minecraft:stone_stairs[facing=east,half=bottom]',
    ),
]

invalid_blockstates = [
    (r"foo[",),
    (r"minecraft:foo[",),
]


class TestSchemlibBlockState(unittest.TestCase):
    @parameterized.expand(blockstate_strings)
    def test_parse_blockstate_from_string(self, str_value: str, expected_value: blocks.BlockState, expected_str_value: str | None = None):
        self.assertEqual(blocks.BlockState.from_string(str_value), expected_value)

    @parameterized.expand(blockstate_strings)
    def test_parse_blockstate_to_string(self, str_value: str, expected_value: blocks.BlockState, expected_str_value: str | None = None):
        self.assertEqual(str(expected_value), expected_str_value or str_value)
        self.assertEqual(expected_value.to_string(), expected_str_value or str_value)

    @parameterized.expand(blockstate_strings)
    def test_parse_blockstate_equal_to_string(self, str_value: str, expected_value: blocks.BlockState, expected_str_value: str | None = None):
        self.assertEqual(expected_value, str_value)

    @parameterized.expand(invalid_blockstates)
    def test_parse_invalid_blockstate_raises_ValueError(self, invalid_blockstate: str):
        with pytest.raises(ValueError, match=re.escape(f"{invalid_blockstate} is an invalid blockstate representation")):
            blocks.BlockState.from_string(invalid_blockstate)

    def test_blockstate_valid_as_dict_key(self):
        air_block = blocks.BlockState(Name="minecraft:air")
        stone_block = blocks.BlockState(Name="minecraft:stone")

        d = {air_block: 0}
        self.assertEqual(d[air_block], 0)

        with pytest.raises(KeyError):
            d[stone_block]
            
    def test_blockstate_as_compound_name_as_tag(self):
        air_block = blocks.BlockState(Name="minecraft:air")
        compound = nbt.model_to_compound(air_block)
        self.assertIsInstance(compound["Name"], nbt.String)
            
    def test_blockstate_as_compound_name_as_tag_when_name_is_tag(self):
        air_block = blocks.BlockState(Name=nbt.String("minecraft:air"))
        compound = nbt.model_to_compound(air_block)
        self.assertIsInstance(compound["Name"], nbt.String)
            
    def test_blockstate_as_compound_skips_empty_properties(self):
        air_block = blocks.BlockState(Name="minecraft:air")
        self.assertEqual(nbt.model_to_compound(air_block), nbt.Compound({"Name": nbt.String("minecraft:air")}))
            
    def test_blockstate_as_compound_includes_nonempty_properties(self):
        air_block = blocks.BlockState(Name="minecraft:air", Properties={"foo": "bar"})
        self.assertEqual(nbt.model_to_compound(air_block), nbt.Compound({"Name": nbt.String("minecraft:air"), "Properties": nbt.Compound({"foo": nbt.String("bar")})}))