SNAKE GRAPHICS TEMPLATE
=======================

This folder holds the custom images for the two snakes. Place PNG files into
the `p1` and `p2` folders to give each player their own look.

  assets/p1/   Player 1 (used by the 1-player game, green by default)
  assets/p2/   Player 2 (used in 2-player mode, blue by default)

RECOGNISED FILES (all optional)
-------------------------------

  head.png     The snake head, drawn facing RIGHT.
  body.png     A straight body segment, drawn horizontal (pointing RIGHT).
  corner.png   A 90-degree bend in the body path.
  tail.png     The tail segment, drawn facing LEFT.

  ANIMATED (Aseprite) — optional frame sequences, auto-detected:
    head_0.png, head_1.png, head_2.png, …
    body_0.png, body_1.png, …
    corner_0.png, corner_1.png, …
    tail_0.png, tail_1.png, …
  If `<part>.png` AND `<part>_N.png` both exist, they play in order
  (base first, then _0, _1, …) at 8 fps. If only `<part>_N.png` exist,
  those play alone. Static single-file art keeps working unchanged.

If an image is missing, that part of the snake falls back to the default
colored rectangle, so the game always runs.

IMAGE REQUIREMENTS
-------------------
- Format: PNG (or any pygame-supported format). Use transparency (.png) so the
  board shows behind the snake.
- File name must match exactly (head.png, body.png, corner.png, tail.png,
  or head_0.png … tail_7.png for animations).
- Each image is scaled automatically to cover one board cell (40x40 at 1080p),
  so you can author at any size. Recommended Aseprite canvas: 128x128 or 64x64
  per frame, transparent background.
- Each part is stretched to fill its cell so neighbouring segments meet with no
  seam. Keep the artwork within about a 3:1 aspect ratio; anything more
  elongated than that is letterboxed (centred, aspect kept) instead.
- The whole snake is exactly one cell thick. Your artwork must fill the cell so
  segments line up into a continuous snake: the segments that join have to
  reach the edges they connect on, otherwise a transparent gap shows at the
  joint. In particular the head must reach its back edge and the elbow arms
  must reach the two edges they join.
- body.png and tail.png are turned a quarter turn on load if they are taller
  than they are wide, so their long axis always runs along the direction of
  travel. Author them any way you like.

ASEPRITE EXPORT (snake)
-----------------------
1. Draw facing RIGHT (head mouth/eyes → right, body horizontal L→R edge,
   corner L-edge in → BOTTOM-edge out, tail → left).
2. Animate with tags/frames on one timeline, then:
   File > Export Sprite Sheet:
     - Type: PNG, Trim/Crop: off (keep full canvas so frames align)
     - Output: separate frames as <part>_0.png, <part>_1.png, …
3. Drop the PNGs into assets/p1/ (green Tagalog) and/or assets/p2/
   (blue Bisaya). No code change needed — the game picks them up and
   loops them at 8 fps (desktop + PWA).
4. Keep the sway in mind: the game adds a ±14%-cell slither offset on top
   of your frames, so author segments that tile edge-to-edge.

AUTHORING GUIDES
-----------------

HEAD (head.png)
  Face the eyes / mouth to the RIGHT. The game rotates the image so the head
  always points in the direction the snake is moving.

BODY (body.png)
  Draw a straight horizontal segment, connected from LEFT edge to RIGHT edge of
  the image so segments tile seamlessly. The game rotates it to match the
  direction of travel.

CORNER (corner.png)
  Draw a 90-degree bend where the body enters the image from the LEFT edge and
  exits through the BOTTOM edge. The game rotates it for every direction of
  travel and mirrors it for the other hand, so this single elbow covers both
  right and left turns. Both arms must reach the edges they leave through.

TAIL (tail.png)
  Draw the tail pointing to the LEFT, connected from the RIGHT edge. The game
  rotates it to point away from the body.

HOW IT WORKS (for reference)
----------------------------
The game stores the snake as a list of grid cells. Each frame it:

  1. Works out a slither offset per segment (head locked, ramping towards the
     tail) that bends smoothly instead of snapping apart at a corner.
  2. Draws the tail image rotated to point away from the body.
  3. Draws each middle segment: a body image for straight stretches, a corner
     image for turns.
  4. Draws the head on top, rotated to face the direction of travel.

Because every part is optional, you can start with just `head.png` and keep the
rest as the default rectangles, then add `body.png`, `corner.png` and
`tail.png` one at a time.

To change the fallback colors (when an image is missing), edit
`make_default_assets` in images.py.

BACKGROUND & MAIN MENU TEMPLATE
===============================

The game also supports custom images for the background and main menu. All of
these are optional; when missing, the game keeps its normal code-drawn look.

  assets/background/   (a FOLDER)
      Put any number of .png files here. Each one becomes a full-screen
      background image you can switch between from the in-game BACKGROUND menu
      (use Left/Right or A/D to browse, ENTER/click to select). The scan
      happens when you open the picker, so you can drop a new file in and it
      will appear without restarting.
      A file named menu.png (optional) is only used for the main menu screen.

  assets/food/   (a FOLDER)
      Put any PNG here to change what the snake eats. ALL PNGs in the folder
      now play as an animation in alphabetical order at 6 fps
      (single PNG = static, food_0.png + food_1.png + … = animated).
      Frames are scaled to fill one board cell. Aseprite: export frames as
      food_0.png, food_1.png, … with transparent background. A legacy
      assets/food.png file is also honoured if the folder is empty.

  assets/menu/logo.png
      Replaces the big "SNAKE" title on the menu. Scaled to fit, centered.

  assets/menu/button_<name>.png
      A menu entry's normal image.
  assets/menu/button_<name>_selected.png
      The same entry when it is highlighted.

      <name> is the menu label lowercased with spaces replaced by underscores:
        1_player, 2_player, background, leaderboard, exit
      Buttons are drawn centered on the text's location. Make them roughly
      button-shaped (e.g. 240x54) with a transparent background; they are
      scaled down to fit if too large.

Use transparency (.png) so things layer cleanly. Everything auto-crops empty
borders, so you don't need to trim the artwork yourself.
