"""Audio Oven Triggers.

Generates sound strips in the Video Sequencer from trigger attributes
stored on the points of a mesh object.
"""

import os

import bpy
from bpy.props import (
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup

# Blender's VSE color tags are COLOR_01 ... COLOR_09 (same order as the icons).
COLOR_TAG_NAMES = (
    "Red", "Orange", "Yellow", "Green", "Blue",
    "Violet", "Purple", "Pink", "Brown",
)

COLOR_TAG_ITEMS = [
    (f"COLOR_{i:02d}", name, "", f"SEQUENCE_COLOR_{i:02d}", i - 1)
    for i, name in enumerate(COLOR_TAG_NAMES, start=1)
]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def get_active_sound_strip(context):
    """Return the active sound strip of the scene, or None."""
    sequence_editor = context.scene.sequence_editor
    if sequence_editor is None:
        return None

    strip = sequence_editor.active_strip
    if strip is None or strip.type != 'SOUND':
        return None

    return strip


def get_point_attribute(mesh, name):
    """Return a point-domain attribute of the mesh, or None."""
    attribute = mesh.attributes.get(name)
    if attribute is None or attribute.domain != 'POINT':
        return None
    return attribute


def poll_mesh_object(self, obj):
    return obj.type == 'MESH'


# -----------------------------------------------------------------------------
# Properties
# -----------------------------------------------------------------------------

class AudioOvenProperties(PropertyGroup):
    audio_file: StringProperty(
        name="Audio File",
        description="Audio file used by the trigger system",
        subtype='FILE_PATH',
    )
    trigger_mesh: PointerProperty(
        name="Trigger Mesh",
        description="Mesh object containing the trigger attributes",
        type=bpy.types.Object,
        poll=poll_mesh_object,
    )
    trigger_id: IntProperty(
        name="Trigger ID",
        description="Trigger ID to search for",
        default=1,
        min=1,
    )
    default_volume: FloatProperty(
        name="Default Volume",
        description="Volume used when no valid per-trigger volume exists",
        default=1.0,
        min=0.0,
        max=1.0,
        precision=3,
    )
    color_tag: EnumProperty(
        name="Color Tag",
        description=(
            "Default VSE color tag, used when the mesh has no valid "
            "\"color tag\" attribute value"
        ),
        items=COLOR_TAG_ITEMS,
    )
    from_channel: IntProperty(
        name="From Channel",
        description="First VSE channel available to the trigger system",
        default=1,
        min=1,
        max=128,
    )
    to_channel: IntProperty(
        name="To Channel",
        description="Last VSE channel available to the trigger system",
        default=2,
        min=1,
        max=128,
    )
    start_trim: IntProperty(
        name="Start Trim",
        description="Number of frames removed from the beginning of each audio strip",
        default=0,
        min=0,
    )
    maximum_frame_duration: IntProperty(
        name="Maximum Frame Duration",
        description="Maximum duration of a generated audio strip in frames",
        default=1,
        min=1,
    )


# -----------------------------------------------------------------------------
# Operators
# -----------------------------------------------------------------------------

class AUDIO_OVEN_OT_strip_info_to_trigger_panel(Operator):
    bl_idname = "audio_oven.strip_info_to_trigger_panel"
    bl_label = "Strip Info to Trigger Panel"
    bl_description = "Copy selected sound strip information to the Audio Oven trigger panel"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return get_active_sound_strip(context) is not None

    def execute(self, context):
        strip = get_active_sound_strip(context)
        if strip is None:
            self.report({'ERROR'}, "Active strip is not a sound strip.")
            return {'CANCELLED'}

        props = context.scene.audio_oven

        if strip.sound is not None:
            # Blender returns "//file.wav" for files next to the blend file,
            # so store the full absolute path instead.
            props.audio_file = os.path.normpath(
                bpy.path.abspath(
                    strip.sound.filepath,
                    library=strip.sound.library,
                )
            )

        props.default_volume = strip.volume

        if strip.color_tag != 'NONE':
            props.color_tag = strip.color_tag

        props.start_trim = max(0, round(strip.left_handle_offset))
        props.maximum_frame_duration = max(1, round(strip.duration))

        self.report({'INFO'}, f"Loaded '{strip.name}' into Trigger Panel.")
        return {'FINISHED'}


class AUDIO_OVEN_OT_generate_triggers(Operator):
    bl_idname = "audio_oven.generate_triggers"
    bl_label = "Generate Triggers"
    bl_description = "Generate audio strips from trigger attributes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.audio_oven

        target_id = props.trigger_id
        default_volume = props.default_volume
        default_color_tag = props.color_tag
        start_trim = props.start_trim
        max_duration = props.maximum_frame_duration
        trigger_object = props.trigger_mesh

        from_channel = min(props.from_channel, props.to_channel)
        to_channel = max(props.from_channel, props.to_channel)

        # Validation
        if not props.audio_file:
            self.report({'ERROR'}, "No audio file has been selected.")
            return {'CANCELLED'}

        audio_path = bpy.path.abspath(props.audio_file)
        if not os.path.isfile(audio_path):
            self.report({'ERROR'}, "The selected audio file could not be found.")
            return {'CANCELLED'}

        audio_name = os.path.splitext(os.path.basename(audio_path))[0]

        if trigger_object is None:
            self.report({'ERROR'}, "No trigger mesh has been selected.")
            return {'CANCELLED'}

        if trigger_object.type != 'MESH':
            self.report({'ERROR'}, "The trigger object must be a mesh.")
            return {'CANCELLED'}

        if scene.sequence_editor is None:
            scene.sequence_editor_create()

        sequence_editor = scene.sequence_editor
        if sequence_editor is None:
            self.report({'ERROR'}, "Could not create the Sequence Editor.")
            return {'CANCELLED'}

        # Clear the channels used by the trigger system
        channels = range(from_channel, to_channel + 1)
        for strip in list(sequence_editor.strips_all):
            if strip.channel in channels:
                sequence_editor.strips.remove(strip)

        original_frame = scene.frame_current
        generated_count = 0
        skipped_short_audio = 0

        # Frame at which the last strip generated in each channel ends
        busy_until = {}

        try:
            for current_frame in range(scene.frame_start, scene.frame_end + 1):

                available_channels = [
                    channel for channel in channels
                    if busy_until.get(channel, current_frame) <= current_frame
                ]
                if not available_channels:
                    continue

                scene.frame_current = current_frame
                context.view_layer.update()

                depsgraph = context.evaluated_depsgraph_get()
                mesh = trigger_object.evaluated_get(depsgraph).data

                trigger_ids = get_point_attribute(mesh, "trigger id")
                if trigger_ids is None:
                    continue

                volumes = get_point_attribute(mesh, "volume")
                color_tags = get_point_attribute(mesh, "color tag")

                # Collect one (volume, color tag) pair per matching point
                triggers = []
                for index, item in enumerate(trigger_ids.data):
                    if item.value != target_id:
                        continue

                    volume = default_volume
                    if volumes is not None:
                        value = volumes.data[index].value
                        if 0.0 <= value <= 1.0:
                            volume = value

                    color_tag = default_color_tag
                    if color_tags is not None:
                        value = color_tags.data[index].value
                        if 1 <= value <= 9:
                            color_tag = f"COLOR_{int(value):02d}"

                    triggers.append((volume, color_tag))

                    if len(triggers) == len(available_channels):
                        break

                # Create one strip per trigger
                for (volume, color_tag), channel in zip(triggers, available_channels):
                    strip = sequence_editor.strips.new_sound(
                        name=audio_name,
                        filepath=audio_path,
                        channel=channel,
                        frame_start=current_frame - start_trim,
                    )

                    if strip.duration <= start_trim:
                        sequence_editor.strips.remove(strip)
                        skipped_short_audio += 1
                        continue

                    strip.left_handle_offset = start_trim

                    if strip.duration > max_duration:
                        strip.right_handle_offset = strip.duration - max_duration

                    strip.left_handle = current_frame
                    strip.volume = volume
                    strip.color_tag = color_tag

                    busy_until[channel] = strip.right_handle
                    generated_count += 1

        finally:
            scene.frame_current = original_frame
            context.view_layer.update()

        if generated_count == 0:
            self.report({'WARNING'}, "No trigger was added.")
            return {'FINISHED'}

        message = f"Generated {generated_count} trigger(s)."
        if skipped_short_audio > 0:
            message += f" {skipped_short_audio} audio strip(s) were too short."
        self.report({'INFO'}, message)

        return {'FINISHED'}


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

class AUDIO_OVEN_PT_trigger(Panel):
    bl_label = "trigger"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Audio Oven"

    def draw(self, context):
        layout = self.layout
        props = context.scene.audio_oven

        # (row heading, property name)
        fields = (
            ("audio :", "audio_file"),
            ("trigger mesh:", "trigger_mesh"),
            ("trigger id :", "trigger_id"),
            ("default volume :", "default_volume"),
            ("default color tag :", "color_tag"),
            ("from channel:", "from_channel"),
            ("to channel:", "to_channel"),
            ("start trim :", "start_trim"),
            ("maximum frame duration", "maximum_frame_duration"),
        )

        for heading, prop_name in fields:
            row = layout.row(heading=heading)
            row.use_property_split = False
            row.use_property_decorate = False
            row.prop(props, prop_name, text="")

        layout.operator("audio_oven.generate_triggers", text="generate triggers")


def draw_strip_info_to_trigger_panel(self, context):
    if get_active_sound_strip(context) is None:
        return

    layout = self.layout
    layout.separator()
    layout.operator(
        "audio_oven.strip_info_to_trigger_panel",
        text="Strip Info to Trigger Panel",
        icon='SOUND',
    )


# -----------------------------------------------------------------------------
# Registration
# -----------------------------------------------------------------------------

classes = (
    AudioOvenProperties,
    AUDIO_OVEN_OT_strip_info_to_trigger_panel,
    AUDIO_OVEN_OT_generate_triggers,
    AUDIO_OVEN_PT_trigger,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.audio_oven = PointerProperty(type=AudioOvenProperties)
    bpy.types.SEQUENCER_MT_context_menu.append(draw_strip_info_to_trigger_panel)


def unregister():
    bpy.types.SEQUENCER_MT_context_menu.remove(draw_strip_info_to_trigger_panel)
    del bpy.types.Scene.audio_oven

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
