import unittest
from typing import Optional

import fauxfactory
import pytest
from PyMCTranslate import Version, new_translation_manager

from schemlib.blocks import Block, BlockPos
from schemlib.entities import Entity
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic


class DummyRegion(AbstractRegion):
    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        raise NotImplementedError
    
    def get_entity_matrix(self) -> dict[tuple[float, float, float], Entity]:
        raise NotImplementedError
    
    def get_tile_entity_matrix(self) -> dict[tuple[int, int, int], Entity]:
        raise NotImplementedError
    
    def get_minecraft_version(self) -> Version:
        return new_translation_manager().get_version("java", (1, 20, 1))

    def get_origin(self) -> BlockPos:
        raise NotImplementedError


class DummySchematic(AbstractSchematic):
    @classmethod
    def get_format_description(cls):
        raise NotImplementedError

    @classmethod
    def get_default_extension(cls):
        raise NotImplementedError
    
    @classmethod
    def get_default_version(cls) -> Version:
        raise NotImplementedError

    @classmethod
    def from_schematic(cls, schematic: AbstractSchematic, target_version: Optional[Version]):
        raise NotImplementedError

    @classmethod
    def schematic_load(cls, obj: object | str | bytes):
        raise NotImplementedError

    def get_metadata(self):
        raise NotImplementedError

    def get_name(self):
        raise NotImplementedError
    
    def get_regions(self):
        raise NotImplementedError

    def schematic_dump(self):
        raise NotImplementedError

    def get_minecraft_version(self) -> Version:
        raise NotImplementedError
    
    
class RegionWithGetBlocks(DummyRegion):
    __blocks__: list[Block]
    
    def __init__(self, blocks) -> None:
        self.__blocks__ = blocks
    
    def get_block_matrix(self) -> dict[tuple[int, int, int], Block]:
        return {block.pos.astuple(): block for block in self.__blocks__}
        
    def get_origin(self):
        return BlockPos(x=0, y=0, z=0)
    
AIR_BLOCK = Block.model_validate({"pos": {"x": 0, "y": 0, "z": 0}, "state": {"Name": "minecraft:air"}})
RegionWithOneAirBlock = RegionWithGetBlocks([AIR_BLOCK])
    
    
class SchematicWithGetRegions(DummySchematic):
    __regions__: list[AbstractRegion]
    
    def __init__(self, regions) -> None:
        self.__regions__ = regions
        
    def get_regions(self):
        return self.__regions__


class TestSchemlibAbstractSchematic(unittest.TestCase):
    def setUp(self):
        self._translation_manager = new_translation_manager()
        self._minecraft_version = self._translation_manager.get_version("java", (1, 20, 1))

    def test_cannot_instantiate_abstract_schematic(self):
        with pytest.raises(TypeError):
            AbstractSchematic()  # type: ignore
        
    def test_schematic_get_region(self):
        schem = SchematicWithGetRegions([RegionWithOneAirBlock])
        self.assertEqual(schem.get_region(0), RegionWithOneAirBlock)

    def test_get_block_matrix(self):
        schem = SchematicWithGetRegions([RegionWithOneAirBlock])
        self.assertEqual(schem.get_region(0).get_block_matrix(), {(0, 0, 0): AIR_BLOCK})

    def test_default_check_size_passes(self):
        AbstractSchematic.check_size(1 << 64, 1 << 64, 1 << 64)

    def test_get_translation_manager(self):
        schem = DummySchematic()
        self.assertIs(schem.get_translation_manager(), schem.get_translation_manager())

    def test_get_palette(self):
        schem = SchematicWithGetRegions([RegionWithOneAirBlock])
        self.assertEqual(schem.get_region(0).get_palette(), [AIR_BLOCK.state])
        
    def test_get_size_empty(self):
        schem = SchematicWithGetRegions([RegionWithGetBlocks([])])
        self.assertEqual(schem.get_region(0).get_size(), (0, 0, 0))

    def test_get_size_one_block(self):
        schem = SchematicWithGetRegions([RegionWithOneAirBlock])
        self.assertEqual(schem.get_region(0).get_size(), (1, 1, 1))
        
    def test_get_size_random_blocks(self):
        p0 = (
            fauxfactory.gen_integer(min_value=-128, max_value=127),
            fauxfactory.gen_integer(min_value=-128, max_value=127),
            fauxfactory.gen_integer(min_value=-128, max_value=127),
        )
        
        p1 = (
            fauxfactory.gen_integer(min_value=-128, max_value=127),
            fauxfactory.gen_integer(min_value=-128, max_value=127),
            fauxfactory.gen_integer(min_value=-128, max_value=127),
        )
        
        size = (
            abs(p0[0] - p1[0]) + 1,
            abs(p0[1] - p1[1]) + 1,
            abs(p0[2] - p1[2]) + 1,
        )
        
        randomized_stone_block_1 = Block.model_validate({
            "pos": {
                "x": p0[0],
                "y": p0[1],
                "z": p0[2],
            },
            "state": {"Name": "minecraft:stone"}
        })
        
        randomized_stone_block_2 = Block.model_validate({
            "pos": {
                "x": p1[0],
                "y": p1[1],
                "z": p1[2],
            },
            "state": {"Name": "minecraft:stone"}
        })
        
        schem = SchematicWithGetRegions([RegionWithGetBlocks([randomized_stone_block_1, randomized_stone_block_2])])
        self.assertEqual(schem.get_region(0).get_size(), size)
        
    def test_get_bounding_box_empty(self):
        schem = SchematicWithGetRegions([RegionWithGetBlocks([])])
        self.assertEqual(schem.get_region(0).get_bounding_box(), (BlockPos.ORIGIN, BlockPos.ORIGIN))
        
    def get_bounding_box_one_block(self):
        schem = SchematicWithGetRegions([RegionWithOneAirBlock])
        self.assertEqual(schem.get_region(0).get_bounding_box(), ((0, 0, 0), (0, 0, 0)))
        
    def test_get_bounding_box_random_blocks(self):
        p0 = (
            fauxfactory.gen_integer(min_value=-128, max_value=0),
            fauxfactory.gen_integer(min_value=-128, max_value=0),
            fauxfactory.gen_integer(min_value=-128, max_value=0),
        )
        
        p1 = (
            fauxfactory.gen_integer(min_value=0, max_value=127),
            fauxfactory.gen_integer(min_value=0, max_value=127),
            fauxfactory.gen_integer(min_value=0, max_value=127),
        )
        
        randomized_stone_block_1 = Block.model_validate({
            "pos": {
                "x": p0[0],
                "y": p0[1],
                "z": p0[2],
            },
            "state": {"Name": "minecraft:stone"}
        })
        
        randomized_stone_block_2 = Block.model_validate({
            "pos": {
                "x": p1[0],
                "y": p1[1],
                "z": p1[2],
            },
            "state": {"Name": "minecraft:stone"}
        })
        
        schem = SchematicWithGetRegions([RegionWithGetBlocks([randomized_stone_block_1, randomized_stone_block_2])])
        self.assertEqual(schem.get_region(0).get_bounding_box(), (p0, p1))