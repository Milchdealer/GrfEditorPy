"""ACT animation format parser.

Reference: GRF/FileFormats/ActFormat/ActConverter.cs, ActHeader.cs
"""
from __future__ import annotations
import math
import struct
from dataclasses import dataclass, field


@dataclass
class ActLayer:
    offset_x: int = 0
    offset_y: int = 0
    sprite_index: int = -1   # -1 = no sprite
    mirror: bool = False
    color: tuple = (255, 255, 255, 255)   # RGBA
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: int = 0        # degrees
    sprite_type: int = 0     # 0 = Indexed8, 1 = Bgra32
    width: int = 0
    height: int = 0


@dataclass
class ActFrame:
    layers: list[ActLayer] = field(default_factory=list)
    sound_id: int = -1


@dataclass
class ActAction:
    frames: list[ActFrame] = field(default_factory=list)
    animation_speed: float = 4.0   # timer interval = speed * 25 ms


@dataclass
class Act:
    version: float
    actions: list[ActAction] = field(default_factory=list)
    sound_files: list[str] = field(default_factory=list)


def parse(data: bytes) -> Act:
    if len(data) < 4 or data[0:2] != b"AC":
        raise ValueError("Not an ACT file")

    minor = data[2]
    major = data[3]
    version = major + minor * 0.1

    pos = 4
    n_actions = struct.unpack_from("<H", data, pos)[0]
    pos = 16  # skip 10 reserved bytes after uint16

    act = Act(version=version)

    for _ in range(n_actions):
        action = ActAction()
        n_frames = struct.unpack_from("<i", data, pos)[0]
        pos += 4

        for _ in range(n_frames):
            pos += 32  # skip unknown block
            frame = ActFrame()
            n_layers = struct.unpack_from("<i", data, pos)[0]
            pos += 4

            for _ in range(n_layers):
                layer = ActLayer()

                if version >= 2.6:
                    layer.offset_x = int(math.floor(struct.unpack_from("<f", data, pos)[0]))
                    layer.offset_y = int(math.floor(struct.unpack_from("<f", data, pos + 4)[0]))
                else:
                    layer.offset_x = struct.unpack_from("<i", data, pos)[0]
                    layer.offset_y = struct.unpack_from("<i", data, pos + 4)[0]
                pos += 8

                layer.sprite_index = struct.unpack_from("<i", data, pos)[0]
                layer.mirror = struct.unpack_from("<i", data, pos + 4)[0] != 0
                pos += 8

                if version >= 2.0:
                    r, g, b, a = data[pos], data[pos + 1], data[pos + 2], data[pos + 3]
                    layer.color = (r, g, b, a)
                    pos += 4

                    layer.scale_x = struct.unpack_from("<f", data, pos)[0]
                    layer.scale_y = layer.scale_x
                    pos += 4

                    if version >= 2.4:
                        layer.scale_y = struct.unpack_from("<f", data, pos)[0]
                        pos += 4

                    layer.rotation = struct.unpack_from("<i", data, pos)[0]
                    layer.sprite_type = struct.unpack_from("<i", data, pos + 4)[0]
                    pos += 8

                    if version >= 2.5:
                        layer.width = struct.unpack_from("<i", data, pos)[0]
                        layer.height = struct.unpack_from("<i", data, pos + 4)[0]
                        pos += 8

                frame.layers.append(layer)

            if version >= 2.0:
                frame.sound_id = struct.unpack_from("<i", data, pos)[0]
                pos += 4

            if version >= 2.3:
                anchor_count = struct.unpack_from("<i", data, pos)[0]
                pos += 4
                pos += anchor_count * 16  # each anchor = 4 unknown + 4+4+4 = 16 bytes

            action.frames.append(frame)

        act.actions.append(action)

    # Sounds block (v2.1+)
    if version >= 2.1 and pos < len(data):
        try:
            n_sounds = struct.unpack_from("<i", data, pos)[0]
            pos += 4
            for _ in range(n_sounds):
                raw = data[pos: pos + 40]
                pos += 40
                null = raw.find(b"\x00")
                act.sound_files.append(raw[:null].decode("latin-1") if null >= 0 else raw.decode("latin-1", errors="replace"))
        except Exception:
            pass

    # Animation speeds (v2.2+)
    if version >= 2.2 and pos < len(data):
        try:
            for action in act.actions:
                if pos + 4 > len(data):
                    break
                action.animation_speed = struct.unpack_from("<f", data, pos)[0]
                pos += 4
        except Exception:
            pass

    return act
