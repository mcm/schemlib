import re
from typing import Any, Callable, ClassVar, Generic, Optional, Self, TypeVar, Union, TYPE_CHECKING, cast

from amulet_nbt import StringTag
from pydantic import BaseModel, Field, field_validator, model_validator
from PyMCTranslate import Version
from PyMCTranslate.py3.api import amulet_objects

from schemlib.nbt import Compound, NbtTag, String

CoordT = TypeVar("CoordT", bound=int | float)


# class AmuletBlock(amulet_objects.block.Block):
#     @classmethod
#     def map_variant_to_material(cls, namespace: str, base_name: str, variant: str):
#         if namespace == "minecraft" and base_name == "stone_slab" and variant == "stone":
#             return "smooth_stone"
#         return variant
    
#     @classmethod
#     def map_material_to_variant(cls, namespace: str, base_name: str, material: str):
#         if namespace == "minecraft" and base_name == "stone_slab" and material == "smooth_stone":
#             return "stone"
#         return material
    
#     @classmethod
#     def from_block(cls, block: "Block") -> Self:
#         namespace, _, base_name = block.state.Name.partition(":")
#         props: dict[str, str] = {k: v for (k, v) in block.state.Properties.items()}
        
#         if "variant" in props:
#             props["material"] = cls.map_variant_to_material(namespace, base_name, props.pop("variant"))
#         if "slab" in base_name and "half" in props:
#             props["type"] = props.pop("half")
        
#         return cls(
#             namespace,
#             base_name,
#             properties={k: StringTag(v) for (k, v) in props.items()}
#         )
        
#     def to_block(self, to_version: Version, pos: "BlockPos", get_block_callback: Optional[Callable[["BlockPos"], "Block"]]=None):
#         def get_block_at_pos(relative_pos: tuple[int, int, int]):
#             if get_block_callback is None:
#                 return AmuletBlock("minecraft", "air"), None
#             target_pos = pos + relative_pos
#             block: Block = get_block_callback(target_pos)
#             return AmuletBlock.from_block(block), None
        
#         block, _, _ = to_version.block.from_universal(
#             self,
#             force_blockstate=True,
#             get_block_callback=get_block_at_pos
#         )
#         block = cast(amulet_objects.block.Block, block)
        
#         # if not is_complete:
#         #     msg = "Unable to convert block due to missing entity or position information"
#         #     raise ValueError(msg)
#         props: dict[str, str] = {k: v.py_data for (k, v) in block.properties.items()}
        
#         if "material" in props:
#             props["variant"] = self.map_material_to_variant(block.namespace, block.base_name, props.pop("material"))
#         if "slab" in block.base_name and "type" in props:
#             props["half"] = props.pop("type")
            
#         return Block(
#             pos=pos,
#             state=BlockState(
#                 Name=block.namespaced_name,
#                 Properties=props
#             )
#         )
        
#         # return Block(pos=pos, state=BlockState(
#         #     Name=translated_block.namespaced_name,
#         #     Properties={k: str(v.py_data) for (k, v) in translated_block.properties.items()}
#         # ))


class AbstractPos(BaseModel, Generic[CoordT]):
    x: CoordT
    y: CoordT
    z: CoordT
    
    @model_validator(mode="wrap")
    @classmethod
    def validate_from_tuple(cls, data, handler):
        if isinstance(data, tuple):
            data = {"x": data[0], "y": data[1], "z": data[2]}
        return handler(data)

    def astuple(self):
        return (self.x, self.y, self.z)

    def __add__(self, other: Self | tuple[CoordT, CoordT, CoordT]) -> Self:
        return self.model_validate(
            {
                "x": self.x + other[0],
                "y": self.y + other[1],
                "z": self.z + other[2],
            }
        )

    def __sub__(self, other: Self | tuple[CoordT, CoordT, CoordT]) -> Self:
        return self.model_validate(
            {
                "x": self.x - other[0],
                "y": self.y - other[1],
                "z": self.z - other[2],
            }
        )

    def __getitem__(self, idx: int) -> CoordT:
        return self.astuple()[idx]
    
    def __eq__(self, value: object) -> bool:
        if not (isinstance(value, AbstractPos | tuple)):  # pragma: nocover
            return super().__eq__(value)
        return (self.x == value[0] and self.y == value[1] and self.z == value[2])


class Block(BaseModel):
    pos: "BlockPos"
    state: "BlockState"

    @property
    def name(self):
        return self.state.Name
    
    # @property
    # def namespace(self):
    #     return self.state.Name.split(":", 1)[0]
    
    # @property
    # def base_name(self):
    #     return self.state.Name.split(":", 1)[1]
    
    # def to_version(self, from_version: Version, to_version: Version):
    #     namespace, base_name = self.state.Name.split(":", 1)
        
    #     amulet_block = amulet_objects.Block(
    #         namespace,
    #         base_name,
    #         self.state.amulet_properties
    #     )
    #     print(str(self.state), amulet_block.blockstate)
        
    #     # Convert block to Amulet universal
    #     universal_block, _, _ = from_version.block.to_universal(amulet_block, force_blockstate=True)
    #     universal_block = cast(amulet_objects.Block, universal_block)
    #     print(universal_block.blockstate)
        
    #     # Convert Amulet universal to Amulet versioned
    #     translated_block, _, _ = to_version.block.from_universal(universal_block, force_blockstate=True)
    #     translated_block = cast(amulet_objects.Block, translated_block)
    #     print(translated_block.blockstate)
        
    #     return Block(
    #         pos=self.pos,
    #         state=BlockState.from_string(translated_block.blockstate)
    #     )


class BlockPos[T: int](AbstractPos[T]):
    ORIGIN: ClassVar["BlockPos"]
    
    if TYPE_CHECKING:  # pragma: nocover
        def __add__(self, other: Union["BlockPos", tuple[int, int, int]]) -> Self: ...
        def __sub__(self, other: Union["BlockPos", tuple[int, int, int]]) -> Self: ...


BlockPos.ORIGIN = BlockPos(x=0, y=0, z=0)


class BlockState(BaseModel):
    Name: String
    Properties: Compound[String] = Field(default_factory=Compound)
    AIR_BLOCK: ClassVar["BlockState"]
    
    @field_validator("Properties", mode="after")
    @classmethod
    def validate_values_are_nbt(cls, value):
        for k in value:
            if isinstance(value[k], NbtTag):
                continue
            value[k] = String(value[k])
        return value
    
    def model_dump_nbt(self, name: Optional[str]=None):
        as_dict: dict[str, Any] = {}
        as_dict["Name"] = String(self.Name)
        if self.Properties:
            as_dict["Properties"] = self.Properties
        return Compound(as_dict)

    @classmethod
    def from_string(cls, v: str):
        m = re.match(r"^(\w+:\w+)(?:\[(.+?)?\])?$", v)
        if m is None:
            msg = f"{v} is an invalid blockstate representation"
            raise ValueError(msg)

        name, props = m.groups()

        properties = {}
        if props:
            for p in props.split(","):
                k, _, v = p.strip().partition("=")
                v = v.strip('"')
                
                properties[k] = v

        return cls(Name=name, Properties=properties)

    def to_string(self) -> str:
        if not self.Properties:
            return self.Name
        
        props = {k: self.Properties[k] for k in sorted(self.Properties.keys())}
        props_as_str = ",".join([f'{k}={props[k]}' for k in props])
        return f"{self.Name}[{props_as_str}]"

    def __str__(self):
        return self.to_string()

    def __hash__(self):
        return hash(self.to_string())

    def __eq__(self, other):
        if isinstance(other, str):
            other = BlockState.from_string(other)
        return super().__eq__(other)


BlockState.AIR_BLOCK = BlockState(Name="minecraft:air")