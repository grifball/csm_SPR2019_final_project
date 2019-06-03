Scott Griffy  
Computers, Sound, and Music - Spring 2019  
Final Project  
Professor: Bart Massey  
Instructor: Leila Hawana  
  
## Overview ##
This project creates a song (.wav) from a .mus file.  
The .mus file is in a special format that I made up  
Each line in the .mus file is another track in the song  
Each track is made up of instructions  
An instruction could be a note to add to the track, a chord, or another instruction that affects the track  
a-g and A-G play individual notes, with the capital letters being an octave higher  
for example, the first few bars for "Ode to Joy" could be written like so:  

    eefggfedccdeedd

If you write this string to a file and supply it as the first parameter for `scott_synth.py` it will create an audio file of "Ode to Joy" (without correct timing)  
Numbers are interpreted as timing changes and apply a note length to all following notes (until another note length change)  
These numbers change the note length to be 1/x of a bar (where 'x' is the number)  
For example, a '2' will change all following notes into half notes  
To play "Ode to Joy" with timing changes, you need to modify the last bar to have a dotted quarter note, and 8th note, and a half note, as shown below:  

    eefg gfed ccde 4.e8d2d

An implied '4' is at the start of every file, meaning notes will default to quarter notes (until you specify another note length)  
Spacing can always be added between instructions to help with the readability.
There are more examples in the `mus_files` directory. These examples use most of the features of the synth.  
A '`@`' or '`#`' symbol after a note indicates a flat or sharp respectively  
Here is a chromatic scale written with sharps and flats (an '`a@`' currently rolls over to be the highest note):  

    aa#bcc#dd#eff#gg#AB@BCD@DE@EFG@Ga@

Chords can be played by specifying a 'M' or 'm' after a note. The following will produce the chords in the "4 chord song"  

    cMgMamfM

Capitalizing these chords will shift them up an octave:  

    CMGMAmFM

Using the 'o' instruction ('o' followed by a number) will shift the base octave up or down. An implied 'o4' is at the start of each file.  
This file is equivalent to `cMgMamfM`:  

    o3CMGMAmFM

Specifying 'n' after a chord will modify it to be inverted. This is the only instruction that occurs after the chord it modifies.  

    CMgMn2Amn2fMn1

Again, you can always add spaces to make the `.mus` file more readable. Unless you put a space in the middle of a single instruction/chord label.  
Here's an equivalent `.mus` string of the inversion example.  

    CM gMn2 Amn2 fMn1

## Instructions ##
Most instructions are written with a single letter immediately followed by a number.  
Here are all (non-global) instructions:  
`i`: changes the instrument. `i1` changes to organ (default). `i0` changes to guitar.  
`n`: invert the last chord (example above)  
`r`: insert a rest (uses current note length, so 4r will insert a quarter note rest)  
`o`: Change the octave (example above). o4 will bring us to a "normal" octave (where 'a' is 440 hertz). You can also do relative changes with `o-1` and `o+1`.  
`v`: Change the volume of following notes. This ranges from 0-100. You can push it higher, it's all relative.  
## Global instructions ##
These are instructions that modify the whole song (not just a single track or following notes). If the same global instruction is used in a song, the earlier ones will be discarded.  
`t`: Change the tempo (in BPM). Defaults to 120  
`l`: Change the global volume. After the song is complete, the volume is normalized (so the max is '1'). If a softer song is desired, this global volume can do that, whereas changing the volume of notes with the `v` instruction cannot. This global volume ranges from 0-100. If you specify a value higher than 100 your wav file will have clipping.  
I'd suggest putting these global instructions on their own "track" (line) at the start of the song.  
You CAN'T supply decimals to any of these instructions.  

## Contributing ##
As far as the programming, the internal structure of songs is setup like so:  
Songs can have multiple tracks.  
Tracks can have multiple sequential chords.  
Chords can have independent lengths (time) and instruments. Each chord can also modify instrument parameters (like envelope) but this is unused.  
All of this is represented by a string format (defined above).  

The parsing code will fall apart if any more features are added. I suggest using a real parser/lexer and tokens.  

The makefile will give a list of options as the default option (just running `make`)  
You can also install python packages yourself and run a test with:  

    $ python3 ./scott_synth.py mus_files/peachs_castle.mus ./peachs_castle.wav

Also, I always use `ffmpeg` to convert them to mp3's:

    $ python test.py mus_files/foreplay_long_time.mus ./foreplay_long_time.wav && yes | ffmpeg -i ./foreplay_long_time.wav foreplay_long_time.mp3

I'm releasing this under the MIT license (https://opensource.org/licenses/MIT)
