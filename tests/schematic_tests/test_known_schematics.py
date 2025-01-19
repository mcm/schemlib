import unittest

from parameterized import parameterized, parameterized_class
from PyMCTranslate import Version

from schemlib.blocks import BlockPos
from schemlib.schematic_formats import AbstractRegion, AbstractSchematic
from schemlib.schematic_formats.building_gadgets import BuildingGadgetsV0Schematic, BuildingGadgetsV1Schematic, BuildingGadgetsV2Schematic
from schemlib.schematic_formats.litematic import LitematicSchematic
from schemlib.schematic_formats.sponge import SpongeSchematicV1, SpongeSchematicV2
from schemlib.schematic_formats.structure import StructureSchematic


schematics = [
    # ("one_stone_block.json", ),
    ("one_stone_block.litematic", LitematicSchematic),
    ("one_stone_block.nbt", StructureSchematic),
    ("one_stone_block_bg0.txt", BuildingGadgetsV0Schematic),
    ("one_stone_block_bg1.txt", BuildingGadgetsV1Schematic),
    ("one_stone_block_bg2.txt", BuildingGadgetsV2Schematic),
    ("one_stone_block_v1.schem", SpongeSchematicV1),
    ("one_stone_block_v2.schem", SpongeSchematicV2),
    # ("one_stone_block_v3.schem", ),
    
    # ("example_bg0_modded_schematic.txt", BuildingGadgetsV0Schematic),
    # ("example_bg0_schematic.txt", BuildingGadgetsV0Schematic),
    # ("example_bg1_schematic.txt", BuildingGadgetsV1Schematic),
    # ("example_bg1_schematic2.txt", BuildingGadgetsV1Schematic),
    # ("example_bg1_schematic3.txt", BuildingGadgetsV1Schematic),
    # ("example_bg2_schematic.txt", BuildingGadgetsV2Schematic),
    # ("example_bg2_schematic2.txt", BuildingGadgetsV2Schematic),
]


target_classes = {target_class for (_, target_class) in schematics if target_class is not BuildingGadgetsV0Schematic}


@parameterized_class(("schematic_filename", "schematic_type"), schematics)
class TestSchemlibSchematics(unittest.TestCase):
    schematic_filename: str
    schematic_type: type[AbstractSchematic]
    
    # filename: str
    # schematic_type: type[AbstractSchematic]
    # expected_serialized: str | bytes
    # expected_version: tuple[str, tuple[int, int, int], int]
    # expected_name: str = "One Stone Block"
    # expected_block: Block = Block(pos=BlockPos.ORIGIN, state=BlockState(Name="minecraft:stone", Properties={}))
    # expected_description: str
    # expected_extension: str
    # max_size: tuple[int, int, int, int] = (0, 0, 0, 0)
    
    # @property
    # def stone_block(self):
    #     return STONE_BLOCK.to_version()

    def setUp(self):
        with open(f"tests/schematics/{self.schematic_filename}", "rb") as f:
            self.schematic = self.schematic_type.schematic_load(f.read())

    def test_schematic_loaded(self):
        self.assertIsInstance(self.schematic, self.schematic_type)

    def test_schematic_get_metadata(self):
        metadata = self.schematic.get_metadata()
        if "author" in metadata:
            self.assertEqual(metadata["author"], "Steve McMaster")
        if "description" in metadata:
            self.assertEqual(metadata["description"], "stone block schematic for testing")

    def test_schematic_get_default_extension(self):
        # assume the parsed file is the right default extension
        _, _, ext = self.schematic_filename.rpartition(".")
        
        self.assertEqual(self.schematic_type.get_default_extension(), ext)

    # def test_schematic_get_description(self):
    #     self.assertEqual(self.schematic_type.get_format_description(), self.expected_description)

    # def test_schematic_get_name(self):
    #     self.assertEqual(self.schematic.get_name(), self.expected_name)

    def test_schematic_get_minecraft_version(self):
        minecraft_version = self.schematic.get_minecraft_version()
        self.assertIsInstance(minecraft_version, Version)
            
    def test_schematic_has_one_region(self):
        self.assertEqual(len(self.schematic.get_regions()), 1)
        
    def test_schematic_region_is_abstract_region(self):
        self.assertIsInstance(self.schematic.get_regions()[0], AbstractRegion)

    def test_schematic_region_get_origin(self):
        self.assertEqual(self.schematic.get_regions()[0].get_origin(), BlockPos.ORIGIN)
        
    def test_schematic_region_has_one_stone_block(self):
        blocks = self.schematic.get_regions()[0].get_blocks()
        
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].state.Name, "minecraft:stone")

    def test_schematic_region_get_size(self):
        self.assertEqual(self.schematic.get_regions()[0].get_size(), (1, 1, 1))

    def test_schematic_region_get_bounding_box(self):
        self.assertEqual(self.schematic.get_regions()[0].get_bounding_box(), (BlockPos.ORIGIN, BlockPos.ORIGIN))
        
    @parameterized.expand(target_classes)
    def test_schematic_conversion(self, target_schematic_type: type[AbstractSchematic]):
        if target_schematic_type is self.schematic_type:
            return
        converted_schematic = target_schematic_type.from_schematic(self.schematic, target_schematic_type.get_default_version())
        
        self.assertEqual(converted_schematic.get_region(0).get_size(), self.schematic.get_region(0).get_size())
        self.assertEqual(converted_schematic.get_region(0).get_bounding_box(), self.schematic.get_region(0).get_bounding_box())
        
        blocks = self.schematic.get_regions()[0].get_blocks()
        
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].state.Name, "minecraft:stone")
    
    ##################

    # def test_schematic_region_get_blocks(self):
    #     stone_block = 
        
    #     self.assertEqual(self.schematic.get_regions()[0].get_blocks(), [self.expected_block])
        
    # def test_schematic_max_size(self):
    #     if self.max_size[0] > 0:
    #         with self.assertRaises(ValueError):
    #             self.schematic_type.check_size(self.max_size[0] + 1, 0, 0)
    #     if self.max_size[1] > 0:
    #         with self.assertRaises(ValueError):
    #             self.schematic_type.check_size(0, self.max_size[1] + 1, 0)
    #     if self.max_size[2] > 0:
    #         with self.assertRaises(ValueError):
    #             self.schematic_type.check_size(0, 0, self.max_size[2] + 1)
    #     if self.max_size[3] > 0:
    #         with self.assertRaises(ValueError):
    #             self.schematic_type.check_size(self.max_size[0] - 1, self.max_size[1] - 1, self.max_size[2] - 1)

    # def test_schematic_dump(self):
    #     self.assertEqual(self.schematic.schematic_dump(), self.expected_serialized)