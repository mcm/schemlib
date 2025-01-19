import json

from schemlib import nbt, snbt
from schemlib.schematic_formats.abstract import AbstractRegion, AbstractSchematic


def get_schematic_type(v):
    def check(o, k):
        if isinstance(o, (dict, nbt.Compound)):
            return k in o
        return hasattr(o, k)
    
    content_type = None
    
    if isinstance(v, (str, bytes)):
        try:
            v = json.loads(v)
            content_type = "json"
        except:
            try:
                v = nbt.load_nbt_from_bytes(v.encode() if isinstance(v, str) else v)
                content_type = "nbt"
            except:
                if isinstance(v, bytes):
                    v = v.decode()
                try:
                    v = snbt.from_snbt(v)
                    content_type = "snbt"
                except:
                    raise TypeError(type(v), v)
    
    if content_type == "json" and check(v, "header"):
        return "BuildingGadgets[1.14.4-1.19.3]"
    elif content_type == "snbt" and check(v, "stateIntArray"):
        return "BuildingGadgets[1.12]"
    elif content_type == "json" and check(v, "statePosArrayList"):
        return "BuildingGadgets2[1.20+]"
    
    if content_type == "json" and check(v, "minecraft_version"):
        return "JSON"
    
    if content_type == "nbt" and check(v, "Regions"):
        return "Litematic"
    
    if content_type == "nbt" and check(v, "required_mods"):
        return "StructurizeBlueprint"
    
    if content_type == "nbt" and getattr(v, "name", None) == "Schematic":
        return f"Sponge[v{v['Version'].to_obj()}]"
    
    # if check(v, "Schematic"):
    #     if isinstance(v, dict):
    #         v = v["Schematic"]
    #     elif isinstance(v, amulet_nbt.CompoundTag):
    #         v = v.get_compound("Schematic")
    #     else:
    #         v = getattr(v, "Schematic")
            
    # if all([check(v, k) for k in ("Version", "Metadata", "Offset")]):
    #     if isinstance(v, dict):
    #         version = v["Version"]
    #     elif isinstance(v, amulet_nbt.CompoundTag):
    #         version = v.get("Version")
    #     else:
    #         version = getattr(v, "Version")
            
    #     if version is None:
    #         raise ValueError(version)
        
    #     return f"Sponge[v{version}]"
    
    if content_type == "nbt" and check(v, "blocks") and check(v, "DataVersion"):
        return "Structure"
    
    raise TypeError(type(v), v)


__all__ = [
    "AbstractRegion",
    "AbstractSchematic",
    "get_schematic_type",
]