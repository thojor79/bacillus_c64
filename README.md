# bacillus_c64
Jump and run game for the C64.
Control a bacillus to hunt for food.

How to run the game?
Of course it works perfectly in the VICE emulator, e.g. under Linux start it
with:

x64 --autostart bacillus.prg

Note that the .prg file is already available in the code repository.

For a real C64 there are various possibilities. First is to use the existing
.D64 disk image file (generated with  make bacillus.d64  or already
available) and transfer it with X1541 to a real floppy disk and load
the game with read hardware. Or use the floppy emulator hardware with SD
cards etc.

For example use OpenCBM and its program d64copy to transfer the .D64 files:

d64copy bacillus.d64 8

for a drive connected via a X(U)1541 cable or device.

Technical facts:
* 2-way side scrolling game (smooth 50 fps)
* parallax scrolling
* animated background and level data
* animated characters
* bonus collecting
* score accounting
* intro
* main screen
* two levels
* special tiles that vaporize
* special boni like invulnerability and 1-up
* dying animation

Planned:
* Outtro
* Highscore handling in mainscreen
* More levels (planned 3-6)
* More level graphics
* More enemies
* Music/Sfx

![ScreenShot](screenshots/level1.jpg)
![ScreenShot](screenshots/intro.jpg)
![ScreenShot](screenshots/mainmenu.jpg)
![ScreenShot](screenshots/dyinganimation.jpg)
![ScreenShot](screenshots/candyworld.jpg)
