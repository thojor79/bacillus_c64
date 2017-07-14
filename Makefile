# Makefile
# fixme maybe put source in src/ subdir
# Store data in data/ dir, convert with c64fy.py, generate .a files

# specify data files explicitly

bacillus.prg : src/game.a src/macros.a src/actor.a src/intro.a src/rasterirq.a src/mainscreen.a src/blendin.a src/level.a src/scrolling.a data/textcharset_sprdata.a data/introscreen_rle.a data/mainlogo_rle.a data/cheese_alltiles_chardata.a data/level*sprites_rle.a data/cheese_level*_rle.a
	acme src/game.a
	
bacillus.all : bacillus.prg
	c1541 -format diskname,id d64 bacillus.d64 -attach bacillus.d64 -write bacillus.prg bacillus
	~/c64/exomizer/src/exomizer sfx sys bacillus.prg -o bacillus_x.prg
	c1541 -format diskname,id d64 bacillus_x.d64 -attach bacillus_x.d64 -write bacillus_x.prg bacillus

run : bacillus.prg
	x64 --autostart bacillus.prg

data : gfx/textcharset.png gfx/introscreen.jpg gfx/mainlogo.png gfx/cheese_alltiles.png
	cd gfx && ../convert/c64fy.py -hires 1 -sprite 0 -quiet 1 -color 1 textcharset.png && mv textcharset_sprdata.a ../data && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 introscreen.jpg && mv introscreen_bmpdata_rle.a ../data/introscreen_rle.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -color 1 mainlogo.png && mv mainlogo_bmpdata_rle.a ../data/mainlogo_rle.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -charset 234 -tilewidth 2 -tileheight 2 -color 9 -color 8 -color 7 -datalabels 0 cheese_alltiles.png && mv cheese_alltiles_chardata.a ../data/ && mv cheese_alltiles_fixcolors.a ../data/ && mv cheese_alltiles_tiledata.a ../data/ && cd ..
	rm gfx/*_c64.png gfx/*.a

leveldata : gfx/cheese_level1.png
	cd gfx && ../convert/indexpng_to_data.py cheese_level1.png && mv cheese_level1_rle.a ../data && rm cheese_level1_raw.a && cd ..
	cd gfx && ../convert/indexpng_to_data.py cheese_level2.png && mv cheese_level2_rle.a ../data && rm cheese_level2_raw.a && cd ..

spritedata : gfx/*sprite*
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 4 -color 0 -color 1 -datalabels 0 bacillus_sprite_frames.png && mv bacillus_sprite_frames_sprdata.a ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 4 -hires 1 -datalabels 0 enemy0_sprite_frames.png && cat enemy0_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 4 -color 0 -color 1 -datalabels 0 enemy1_sprite_frames.png && cat enemy1_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy2_sprite_frames.png && cat enemy2_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy3_sprite_frames.png && cat enemy3_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy4_sprite_frames.png && cat enemy4_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy5_sprite_frames.png && cat enemy5_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 4 -hires 1 -datalabels 0 enemy6_sprite_frames.png && cat enemy6_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 4 -color 0 -color 1 -datalabels 0 enemy7_sprite_frames.png && cat enemy7_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy8_sprite_frames.png && cat enemy8_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy9_sprite_frames.png && cat enemy9_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy10_sprite_frames.png && cat enemy10_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy11_sprite_frames.png && cat enemy11_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 4 -hires 1 -datalabels 0 enemy12_sprite_frames.png && cat enemy12_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 4 -color 0 -color 1 -datalabels 0 enemy13_sprite_frames.png && cat enemy13_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy14_sprite_frames.png && cat enemy14_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 0 -hires 1 -datalabels 0 enemy15_sprite_frames.png && cat enemy15_sprite_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	cd gfx && ../convert/c64fy.py -quiet 1 -sprite 4 -color 0 -color 1 -datalabels 0 bacillus_dead_frames.png && cat bacillus_dead_frames_sprdata.a >> ../data/level1_sprites.a && cd ..
	./convert/rlencodedata.py data/level1_sprites.a && rm data/level1_sprites.a
	rm gfx/*.a

clean :
	rm -f bacillus.prg data/*
