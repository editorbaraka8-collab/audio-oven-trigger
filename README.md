# Audio Oven Trigger
Audio Oven Trigger — an animation-driven audio trigger system for Blender through the use of geometry nodes tool inside blender allowing animators to link there animation to the geometry nodes and eventually to the addon to allow the animator to essentially procedurally control when and how the audio of the animation being made is played

**Animation-driven audio triggering for the Blender Video Sequencer.**

Audio Oven Trigger lets you use animation and Geometry Nodes to mark specific frames where sounds should occur. For example, you can detect the moment a ball hits the ground, or the moment two hands clap, and automatically place sound strips in the Video Sequencer at those exact frames.

## Requirements

- **Blender 5.2 or newer**
- A **mesh object** with a Geometry Nodes setup that outputs the trigger attributes described below
- An audio file on disk (**WAV recommended**)

---

## Installation

### From Blender Extensions

1. Open **Edit → Preferences → Get Extensions**.
2. Search for **Audio Oven Trigger**.
3. Click **Install**.
4. Make sure the add-on is enabled.

### From a downloaded ZIP

1. Drag the downloaded `.zip` file into the Blender window.

   Or:

2. Open **Edit → Preferences → Get Extensions**.
3. Click the **dropdown arrow** in the top-right corner.
4. Choose **Install from Disk**.
5. Select the Audio Oven Trigger `.zip`.

The panel is available in:

**3D Viewport → Sidebar (N) → Audio Oven → trigger**

---

# How It Works

Audio Oven Trigger reads trigger information from the **evaluated mesh** produced by your Geometry Nodes modifier.

1. You supply a trigger mesh whose evaluated geometry contains the required trigger attributes.
2. When you press **Generate Triggers**, the add-on steps through every frame from the scene's **Frame Start** to **Frame End**.
3. On each frame, it searches for vertices whose `trigger id` matches the Trigger ID selected in the panel.
4. Each matching vertex creates a sound strip starting on that frame.
5. Generated strips are trimmed, assigned a volume and color tag, and placed on available channels within your selected channel range.
6. Your original current frame is restored when generation finishes.

---

# Trigger Mesh Attributes

All trigger attributes must be on the **Point (vertex) domain**.

The mesh must also be the **final output of the modifier stack**, because the add-on reads the evaluated mesh.

## `trigger id`

This is the required attribute.

The intended vertex that represents a trigger must have a `trigger id` value matching the **Trigger ID** selected in the Audio Oven Trigger panel.

For example:

```text
Trigger ID in panel = 1

Vertex trigger id:
0 → no trigger
0 → no trigger
1 → trigger
0 → no trigger
```

When the value matches, a sound strip is generated on that frame.

## `volume`

An optional floating-point attribute.

The value must be between:

```text
0.0 → 1.0
```

If the attribute does not exist, or the vertex contains a value outside this range, the **Default Volume** from the panel is used.

This allows Geometry Nodes to control the volume of individual triggered sounds.

For example, impact speed can be remapped to `0–1` and stored as the volume.

## `color tag`

An optional integer attribute.

The value must be between:

```text
1 → 9
```

If the attribute does not exist, or the vertex contains a value outside this range, the **Default Color Tag** from the panel is used.

This allows different triggers to receive different VSE colors.

At the moment, Blender's Video Sequencer provides nine color tags, so the attribute is limited to values **1–9**.

### Important

The attribute names must be written exactly as follows:

```text
trigger id
volume
color tag
```

They are lowercase and contain spaces.

---

# Panel Settings

The Audio Oven Trigger panel contains the following settings.

### Audio

The sound file that will be triggered.

### Trigger Mesh

The mesh object containing the trigger attributes.

### Trigger ID

The ID that this generation pass searches for.

You can use a different ID for each sound.

For example:

```text
Impact sound → Trigger ID 1
Clap sound   → Trigger ID 2
Footstep     → Trigger ID 3
```

### Default Volume

The volume used when a valid per-vertex `volume` value is not available.

### Default Color Tag

The VSE color tag used when a valid per-vertex `color tag` value is not available.

### From Channel / To Channel

The range of VSE channels that the trigger system is allowed to use.

The number of available channels determines the maximum number of sounds that can overlap at the same time (**polyphony**).

For example:

```text
From Channel: 1
To Channel: 6
```

allows up to six simultaneously overlapping generated sounds.

### Start Trim

The number of frames removed from the beginning of the audio.

This can be useful when the source audio contains leading silence or an unwanted attack before the sound you want to synchronize.

For example, if the sound has two frames of unwanted material before the actual impact, you can set:

```text
Start Trim: 2
```

### Maximum Frame Duration

The maximum length of each generated sound strip, measured in frames.

---

# Strip Info to Trigger Panel

You can use an existing VSE sound strip to quickly configure the trigger panel.

1. Add a sound strip to the Video Sequencer.
2. Trim it so that only the part of the sound you want to use remains.
3. Right-click the sound strip.
4. Choose **Strip Info to Trigger Panel**.

The add-on copies the strip's:

- Audio file
- Volume
- Color tag
- Start trim
- Duration

into the Audio Oven Trigger panel.

This makes it easy to prepare a sound exactly the way you want before using it as a trigger.

---

# Quick Start

## 1. Create a trigger mesh

Create a mesh object with a **Geometry Nodes modifier**.

## 2. Create the trigger attributes

Inside Geometry Nodes, use **Store Named Attribute** on the **Point** domain to create:

```text
trigger id
```

You can optionally create:

```text
volume
color tag
```

## 3. Mark the trigger frame

Set `trigger id` to your target ID only on the frame where the event occurs.

For example:

```text
Frame 20 → trigger id = 0
Frame 21 → trigger id = 0
Frame 22 → trigger id = 1  ← event
Frame 23 → trigger id = 0
Frame 24 → trigger id = 0
```

## 4. Configure Audio Oven Trigger

In the Audio Oven Trigger panel:

- Choose the audio file.
- Select the trigger mesh.
- Set the Trigger ID.
- Choose the channel range.
- Set the start trim.
- Set the maximum duration.

## 5. Generate

Click:

**Generate Triggers**

The sound strips will appear in the Video Sequencer.

## 6. Adjust and regenerate

If you change the animation or Geometry Nodes setup, you can generate again.

Each generation pass rebuilds the strips in the selected channel range.

---

# Things to Be Careful About

## 1. Existing strips are deleted

Before generating, the add-on removes **every strip in the selected channel range**.

This includes strips you created manually.

For example, if you use:

```text
From Channel: 1
To Channel: 3
```

the add-on clears those channels before generating new triggers.

Keep trigger systems on dedicated channels.

If you accidentally remove something, use **Ctrl+Z** to undo the operation.

---

## 2. Give different triggers their own channel ranges

Two trigger systems should not share the same channel range if you intend to preserve both.

For example:

```text
Impact sounds:
ID 1
Channels 1–6

Snare sounds:
ID 2
Channels 7–9
```

This allows the two trigger systems to be generated independently.

---

## 3. The trigger ID should normally be active for one frame

If a vertex keeps the target trigger ID for multiple frames, the add-on will generate a sound on every one of those frames.

For example:

```text
Frame 20 → ID 1
Frame 21 → ID 1
Frame 22 → ID 1
```

will generate three triggers.

For a single event, the intended setup is normally:

```text
Frame 20 → ID 0
Frame 21 → ID 1  ← trigger
Frame 22 → ID 0
```

---

## 4. Channels determine polyphony

The available channels determine how many generated sounds can overlap.

For example:

```text
Channels 1–3
```

provides three available channels.

If more triggers occur simultaneously than there are available channels, the additional triggers are skipped.

For busy scenes, increase the channel range.

---

## 5. Set an appropriate maximum duration

The default maximum duration is **1 frame**.

If you want longer sounds, increase the value.

For example:

```text
Maximum Frame Duration: 24
```

allows a generated strip to last up to 24 frames.

---

## 6. Keep the output as a mesh with vertices

The trigger system reads the evaluated **mesh**.

Point clouds, curves, and unrealized instances will not be read as trigger meshes.

If using instances in Geometry Nodes, make sure they are realized and that the required attributes remain on the **Point domain**.

---

## 7. The modifier must be enabled in the viewport

The add-on reads the **evaluated mesh** produced by the modifier.

Make sure the Geometry Nodes modifier is enabled in the viewport.

---

## 8. The audio file must exist on disk

The selected audio file must be available on disk.

Packed or missing files will produce an error.

If you are using relative paths, save your `.blend` file first.

---

## 9. Frame range

Audio Oven Trigger processes the scene's:

- **Frame Start**
- **Frame End**

It does **not** use the preview range.

---

## 10. Processing speed

The add-on evaluates the trigger mesh on every frame.

Long frame ranges or heavy Geometry Nodes setups can therefore take some time and may temporarily freeze Blender while the triggers are being generated.

For simulations, baking the simulation first can help improve reliability and performance.

---

## 11. Timing is per whole frame

Trigger timing is evaluated on whole frames.

Sub-frame trigger timing is not supported.

---

## 12. Generated strips are normal VSE sound strips

The generated audio strips are normal Blender Video Sequencer sound strips.

They can therefore be edited normally after generation and will be included in the render mixdown.

---

# Example: Bouncing Objects

Imagine an animation containing **40 balls** falling and bouncing on a floor.

You want every impact to produce a sound.

You also want:

- Hard impacts to be louder.
- Soft impacts to be quieter.
- Sounds from distant objects to be quieter.
- Different types of balls to have different VSE colors.

## 1. Detect the impact

In Geometry Nodes, you can use techniques such as ray casting, geometry proximity, or other animation/simulation logic to determine when a ball contacts the floor.

On the impact frame, the ball's trigger vertex can receive:

```text
trigger id = 1
```

On other frames it receives:

```text
trigger id = 0
```

The trigger logic can be designed to detect the transition into contact rather than continuously marking the ball while it remains on the ground.

For example, you might compare the current state with the previous frame, or use velocity to determine whether the impact is significant enough to produce a sound.

---

## 2. Control impact volume

The impact speed can be remapped to a range from `0–1` and stored as the:

```text
volume
```

attribute.

This means:

- Fast impact → louder sound
- Slow impact → quieter sound

You can also incorporate the distance between the active camera and the geometry so that objects farther from the camera produce quieter sounds.

---

## 3. Control color tags

Different objects can use different color tags.

For example:

```text
Heavy balls → color tag = 2
Light balls → color tag = 6
```

This makes the resulting sound strips easier to identify in the Video Sequencer.

Before generating the triggers, you can also prepare the exact sound you want to use:

1. Add the sound to the VSE.
2. Trim it to the portion you want.
3. Right-click the strip.
4. Select **Strip Info to Trigger Panel**.

The strip information is then copied into the trigger panel.

---

## 4. Configure the trigger

For example:

```text
Audio:                  thud.wav
Trigger Mesh:           ball object
Trigger ID:             1
From Channel:           1
To Channel:             6
Start Trim:             2
Maximum Frame Duration: 24
```

Then click:

**Generate Triggers**

The add-on generates the sound pass automatically from the animation.

---

## 5. Continue editing

After generation, the resulting sound strips are normal VSE strips.

You can still:

- Nudge individual strips
- Mute individual strips
- Adjust individual strips
- Regenerate after changing the animation

---

# Layered Sound Design

You can use multiple trigger IDs and separate channel ranges to build layered sound effects.

For example:

```text
Impact / thud
Trigger ID: 1
Channels: 1–6

Snare
Trigger ID: 2
Channels: 7–9
```

Run the trigger system separately for each sound.

This allows multiple independent sound layers to be generated from the same animation.

---

# Attribute Summary

| Attribute | Domain | Type | Valid Range | Required |
|---|---|---|---|---|
| `trigger id` | Point | Integer | Any integer | **Yes** |
| `volume` | Point | Float | 0–1 | No |
| `color tag` | Point | Integer | 1–9 | No |

If an optional attribute is missing or contains an invalid value, Audio Oven Trigger falls back to the corresponding default value from the panel.

