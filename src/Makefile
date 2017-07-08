# Makefile
# fixme maybe put source in src/ subdir
# Store data in data/ dir, convert with c64fy.py, generate .a files

# fixme specify data for dependencies better
bacillus.prg : game.a macros.a actor.a intro.a rasterirq.a mainscreen.a blendin.a level.a scrolling.a data data/level*sprites.a data/cheese_level1.png_lvldata.a
	acme game.a

run : bacillus.prg
	x64 --autostart bacillus.prg

data : gfx/textcharset.png gfx/introscreen.jpg gfx/mainlogo.png gfx/cheese_alltiles.png
	mkdir -p data
	cd gfx && ../../convert/c64fy.py -hires 1 -sprite 0 -quiet 1 -color 1 textcharset.png && mv output/textcharset_sprdata.a ../data && cd ..
	cd gfx && ../../convert/c64fy.py -quiet 1 introscreen.jpg && mv output/introscreen_bmpdata_rle.a ../data/introscreen_rle.a && cd ..
	cd gfx && ../../convert/c64fy.py -quiet 1 -color 1 mainlogo.png && mv output/mainlogo_bmpdata_rle.a ../data/mainlogo_rle.a && cd ..
	cd gfx && ../../convert/c64fy.py -quiet 1 -charset 236 -firstchar 20 -tilewidth 2 -tileheight 2 -color 9 -color 8 -color 7 -datalabels 0 cheese_alltiles.png && mv output/cheese_alltiles_chardata.a ../data/ && mv output/cheese_alltiles_fixcolors.a ../data/ && mv output/cheese_alltiles_tiledata.a ../data/ && cd ..

leveldata : gfx/cheese_level1.png
	cd gfx && ../makelevel.py cheese_level1.png && mv cheese_level1.png_lvldata.a ../data && cd ..

spritedata : gfx/*sprite*
	cd gfx && ../../convert/c64fy.py -quiet 1 -sprite 4 -color 0 -color 1 -datalabels 0 bacillus_sprite_frames.png && mv output/bacillus_sprite_frames_sprdata.a ../data/level1_sprites.a && cd ..
	cd gfx && ../../convert/c64fy.py -quiet 1 -sprite 4 -color 1 -hires 1 -datalabels 0 enemy0_sprite_frames.png && cat output/enemy0_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../../convert/c64fy.py -quiet 1 -sprite 4 -color 0 -color 1 -datalabels 0 enemy1_sprite_frames.png && cat output/enemy1_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../../convert/c64fy.py -quiet 1 -sprite 0 -color 10 -hires 1 -datalabels 0 enemy2_sprite_frames.png && cat output/enemy2_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../../convert/c64fy.py -quiet 1 -sprite 0 -color 13 -hires 1 -datalabels 0 enemy3_sprite_frames.png && cat output/enemy3_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../../convert/c64fy.py -quiet 1 -sprite 0 -color 14 -hires 1 -datalabels 0 enemy4_sprite_frames.png && cat output/enemy4_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../../convert/c64fy.py -quiet 1 -sprite 0 -color 3 -hires 1 -datalabels 0 enemy5_sprite_frames.png && cat output/enemy5_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..

clean :
	rm -f bacillus.prg data/*
