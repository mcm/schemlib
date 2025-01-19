import unittest

from schemlib.blocks import Block, BlockPos, BlockState
from schemlib.schematic_formats.version_mapping import MinecraftVersionMapper, Version


DIRT_PATH_BLOCK = Block(pos=BlockPos.ORIGIN, state=BlockState(Name="minecraft:dirt_path"))
GRASS_PATH_BLOCK = Block(pos=BlockPos.ORIGIN, state=BlockState(Name="minecraft:grass_path"))
STONE_BLOCK = Block(pos=BlockPos.ORIGIN, state=BlockState(Name="minecraft:stone"))
SPRUCE_SLAB = Block(pos=BlockPos.ORIGIN, state=BlockState(Name="minecraft:spruce_slab", Properties={"type": "top"}))
SPRUCE_WOODEN_SLAB = Block(pos=BlockPos.ORIGIN, state=BlockState(Name="minecraft:wooden_slab", Properties={"half": "top", "variant": "spruce"}))


class TestSchemlibVersionMapping(unittest.TestCase):
    def test_mapping_unchanged_block_returns_block(self):
        block_matrix = {(0, 0, 0): STONE_BLOCK}
        source_version = MinecraftVersionMapper.get_version("1.12.2")
        target_version = MinecraftVersionMapper.get_version("1.20.1")
        mapper = MinecraftVersionMapper(block_matrix, source_version)
        self.assertEqual(mapper.map_block(STONE_BLOCK, target_version), STONE_BLOCK)
        
    def test_mapping_pre_flattening_block_returns_post_flattening_block(self):
        block_matrix = {(0, 0, 0): SPRUCE_WOODEN_SLAB}
        source_version = MinecraftVersionMapper.get_version("1.12.2")
        target_version = MinecraftVersionMapper.get_version("1.13.1")
        mapper = MinecraftVersionMapper(block_matrix, source_version)
        self.assertEqual(mapper.map_block(SPRUCE_WOODEN_SLAB, target_version), SPRUCE_SLAB)
        
    def test_mapping_renamed_block_returns_renamed_block(self):
        block_matrix = {(0, 0, 0): GRASS_PATH_BLOCK}
        source_version = MinecraftVersionMapper.get_version("1.16.2")
        target_version = MinecraftVersionMapper.get_version("1.17.1")
        mapper = MinecraftVersionMapper(block_matrix, source_version)
        self.assertEqual(mapper.map_block(GRASS_PATH_BLOCK, target_version), DIRT_PATH_BLOCK)