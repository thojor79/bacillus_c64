# bacillus_c64
Jump and run game for the C64.
Control a bacillus to hunt for food.

How to run the game?
Of course it works perfectly in the VICE emulator, e.g. under Linux start it
with:
x64 --autostart bacillus.prg
Note that the .prg file is already available in the code repository.

For a real C64 there are various possibilities. One would be to generate a
.D64 disk image and transfer it with X*1541 to a real floppy disk and load
the game with read hardware. Or use the floppy emulator hardware with SD
cards etc. A .D64 image is planned to be provided as well (later).

Technical facts:
* 2-way side scrolling game
* parallax scrolling
* animated background and level data
* animated characters

Planned:
* Intro, Outtro
* Highscore handling
* More levels
* More level graphics
* More enemies
* Boni
* Music/Sfx

![ScreenShot](screenshots/level1.jpg)
![ScreenShot](screenshots/mainmenu.jpg)
