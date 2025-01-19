from dataclasses import dataclass
from typing import Annotated, Any, cast

from amulet_nbt import StringTag
from PyMCTranslate import Version, new_translation_manager
from PyMCTranslate.py3.api import amulet_objects
from pydantic import GetCoreSchemaHandler, GetPydanticSchema
from pydantic_core import core_schema

from schemlib.blocks import Block, BlockPos, BlockState
from schemlib.nbt import String


def serialize_version(value: Version) -> str:
    return ".".join(map(str, value.version_number))


def validate_version(value: Version | str) -> Version:
    if isinstance(value, Version):
        return value
    
    translation_manager = new_translation_manager()
    
    try:
        target_version = translation_manager.get_version("java", [int(x) for x in value.split(".")])
    except:
        msg = f"Unable to parse target version '{value}"
        raise ValueError(msg)
    
    return target_version


class MinecraftVersionPydanticSchema:
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        from_str_schema = core_schema.chain_schema([
            core_schema.str_schema(),
            core_schema.no_info_plain_validator_function(validate_version)
        ])
        
        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(Version),
                from_str_schema
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize_version)
        )
        
        
MinecraftVersion = Annotated[
    Version,
    MinecraftVersionPydanticSchema
]


# MinecraftVersion = Annotated[
#     Version, 
#     GetPydanticSchema(
#         lambda _, handler: core_schema.json_or_python_schema(
#             json_schema=handler(str),
#             python_schema=core_schema.no_info_after_validator_function(
#                 validate_version, 
#                 core_schema.union_schema([
#                     core_schema.is_instance_schema(Version),
#                     handler(str)
#                 ])
#             ),
#             serialization=core_schema.plain_serializer_function_ser_schema(serialize_version)
#         )
#     )
# ]


@dataclass
class MinecraftVersionMapper:
    block_matrix: dict[tuple[int, int, int], Block]
    source_version: Version
    
    @classmethod
    def get_version(cls, version_string: str) -> Version:
        tm = new_translation_manager()
        return tm.get_version("java", tuple(map(int, version_string.split("."))))
    
    def _map_variant_to_material(self, block: Block, variant: amulet_objects.PropertyValueType) -> amulet_objects.PropertyValueType:
        if block.state.Name == "minecraft:stone_slab" and variant.py_data == "stone":
            return StringTag("smooth_stone")
        return variant
    
    def _get_amulet_block(self, block: Block) -> amulet_objects.Block:
        namespace, _, base_name = block.state.Name.partition(":")
        props: dict[str, amulet_objects.PropertyValueType] = {k: StringTag(v) for (k, v) in block.state.Properties.items()}
        
        if "variant" in props:
            props["material"] = self._map_variant_to_material(block, props.pop("variant"))
        if "slab" in base_name and "half" in props:
            props["type"] = props.pop("half")
        
        return amulet_objects.Block(
            namespace,
            base_name,
            properties=props
        )
    
    def get_block_at(self, pos: BlockPos) -> tuple[amulet_objects.Block, None]:  # TODO: Return BlockEntity when needed
        try:
            block = self.block_matrix[pos.astuple()]
            return self._get_amulet_block(block), None
        except KeyError:
            return amulet_objects.Block("minecraft", "air"), None
    
    def map_block(self, block: Block, target_version: Version) -> Block:
        from_block = self._get_amulet_block(block)
        
        universal_block, _, _ = self.source_version.block.to_universal(
            block=from_block,
            force_blockstate=True,
            get_block_callback=lambda relative_pos: self.get_block_at(block.pos + relative_pos)
        )
        universal_block = cast(amulet_objects.Block, universal_block)
        
        if universal_block.namespace != "universal_minecraft":
            # No mapping to do
            return block
        
        translated_block, _, _ = target_version.block.from_universal(
            block=universal_block,
            get_block_callback=lambda relative_pos: self.get_block_at(block.pos + relative_pos)
        )
        translated_block = cast(amulet_objects.Block, translated_block)
        
        return Block(
            pos=block.pos,
            state=BlockState(
                Name=translated_block.namespaced_name,
                Properties={k: String(v.py_data) for (k, v) in translated_block.properties.items()}
            )
        )