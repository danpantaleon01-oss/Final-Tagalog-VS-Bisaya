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

If an image is missing, that part of the snake falls back to the default
colored rectangle, so the game always runs.

IMAGE REQUIREMENTS
-------------------
- Format: PNG (or any pygame-supported format). Use transparency (.png) so the
  board shows behind the snake.
- File name must match exactly (head.png, body.png, corner.png, tail.png).
- Each image is scaled automatically to one board cell (20x20 by default), so
  you can author at any size. Logos / details will be scaled down.
- The whole snake is exactly one cell thick. Your artwork must fit within the
  cell so segments line up into a continuous snake.

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
  exits through the BOTTOM edge. The game rotates it to match every turn.

TAIL (tail.png)
  Draw the tail pointing to the LEFT, connected from the RIGHT edge. The game
  rotates it to point away from the body.

HOW IT WORKS (for reference)
----------------------------
The game stores the snake as a list of grid cells. Each frame it:

  1. Draws the tail image rotated to point away from the body.
  2. Draws each middle segment: a body image for straight stretches, a corner
     image for turns.
  3. Draws the head on top, rotated to face the direction of travel.

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
      Put any PNG here to change what the snake eats. The first image
      (alphabetically) is used and scaled to fill one board cell. A default
      apple (apple.png) is included - replace it or add your own. Use a
      transparent background (.png) so the board shows through. A legacy
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
