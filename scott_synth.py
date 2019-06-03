import sys
import numpy as np
from scipy.io import wavfile
from random import random
import re
from itertools import chain

'''
Scott Griffy's Computers Sound and Music project
This file is an executable that takes in a .mus file and outputs a .wav file
You can test out this file with:
$ echo "4eefg gfed ccde 4.e8d2d" > ode_to_joy.mus
$ python3 scott_synth.py ode_to_joy.mus output.wav
View the README.md file for more information
TODO:
  add key signatures
    this would require adding in naturals and modifying ``chords" (just notes) so they know whether or not to be modified by the key signature after instructions are parsed
  add drums
  add arpeggios
'''

class Chord():
  # This class represents multiple notes played at the same length
  def __init__(self, chord, instr, length, vol=1, env=np.array([.1,.1,.6,.2]), lowPass=1):
    self.chord = chord
    self.instr = instr
    self.length = length
    self.env = env # this array defines the length of segments in the envelope (attack, decay, sustain, release)
    self.lowPass = 1
    self.envVols = np.array([1,.75])*vol # this array defines the volume of the envelope at different points (attack height, sustain)

# invert the first note (make it an octave higher)
def inv(chord, times=1):
  for time in range(0,times):
    chord = np.append(chord[1:],chord[0]+12)
  return chord

# create a chord from notes which uses the organ instrument
def organ(chord,l=1/4,v=1):
  # this accepts a single chord, or an array of chords (flattens itself appropriately)
  if len(chord.shape)>1 and chord.shape[1]>0:
    chords = []
    for ch in chord:
      chords.append(organ(ch, l, v))
    return chords
  return Chord(chord, 1, l, vol=v, lowPass=20)

# create a chord from notes which uses the guitar instrument
def guitar(chord,l=1/4,v=1):
  # like the organ, this accepts a single chord, or an array of chords
  if len(chord.shape)>1 and chord.shape[1]>0:
    chords = []
    for ch in chord:
      chords.append(guitar(ch, l, v))
    return chords
  return Chord(chord, 0, l, env=np.array([0, 0, 1, 0]), lowPass=1)

# this is an instrument too I guess
def rest(chord=None, l=1/4):
  return Chord(np.array([]), 2, l, env=np.array([0, 0, 1, 0]), vol=0)

# map the instruments to indexes
instrumentMap = [guitar, organ, rest]

if len(sys.argv)<3:
  print("gimmie a .mus file to read and a .wav to write out to\nex:\n\tpython "+str(sys.argv[0])+" song_file.mus audio_file.wav")
  sys.exit(1)

# get arguments
fileName = str(sys.argv[1])
wavName = str(sys.argv[2])

# Parsing out the .mus file
songFile = open(fileName, 'r')

# setup a map to convert instructions into chords
chordOrderedMap = []
# I added an agnostic function in case I change how chords are added to the map
def addChordMap(instruc, arr):
  chordOrderedMap.append([instruc, arr])
# setup all the base chords
typesOfChords = [
  ['-5',np.array([0,7])], # I kinda hacked some of these in to write the songs
  ['-#5',np.array([0,8])],
  ['-4',np.array([0,5])],
  ['-#4',np.array([0,6])],
  ['M3',np.array([0,4])],
  ['m3',np.array([0,3])],
  ['M2',np.array([0,2])],
  ['m2',np.array([0,1])],
  ['M',np.array([0,4,7])],
  ['m',np.array([0,3,7])],
  ['M7',np.array([0,4,7,11])],
  ['7',np.array([0,4,7,10])], # this will probably cause ambiguities if a 7th note if ever used... oh well
  ['-7',np.array([0,10])],
  ['M6',np.array([0,4,7,9])],
  ['-6',np.array([0,9])],
  ['m7',np.array([0,3,7,10])],
  ['m6',np.array([0,3,7,9])]
]
# get all the distinct notes (use sharps)
# lowercase and uppercase are used to relieve using octave changes frequently
notesUpper = ['A','A#','B','C','C#','D','D#','E','F','F#','G','G#']
notesLower = [note.lower() for note in notesUpper]
allNotes = notesLower+notesUpper

# this array converts all flats to sharps, makes scores easier to deal with
flatReplace = [
  ['a@', 'G#'], # yeah, this rolls over weird, just have to get used to it
  ['b@', 'a#'],
  ['c@', 'b'],
  ['d@', 'c#'],
  ['e@', 'd#'],
  ['f@', 'e'],
  ['g@', 'f#'],
  ['A@', 'g#'],
  ['B@', 'A#'],
  ['C@', 'B'],
  ['D@', 'C#'],
  ['E@', 'D#'],
  ['F@', 'E'],
  ['G@', 'F#'],
]

# add in all the chords, with all the different roots
#   in two octaves
for note,interval in zip(allNotes,range(0,24)):
  for chordName,chord in typesOfChords:
    addChordMap(note+chordName, chord+interval)
# a note is just a chord with only one note in it
# map this in
for note,interval in zip(allNotes,range(0,24)):
  addChordMap(note, np.array([interval]))

# ensure our chord maps are in order from longest to shortest (for parsing)
chordOrderedMap = sorted(chordOrderedMap, key=lambda x: len(x[0]))
chordOrderedMap = list(reversed(chordOrderedMap))

# setup the parser state variables
# state will continue between tracks (allows for a ``header"-like line)
# that's why they're defined here, outside of the track loop (python may not care about this, but it makes it easier to understand)
tempo = 120
volume = 100
instrumentFunc = organ
octave = 0
tracks = []
speed = 1/4
globalVol = 100
for trackString in songFile:
  if len(trackString)>1 and trackString[0:2] == "//":
    pass # this was a comment string
  else:
    track = []
    segments = [trackString]
    # we will iteratively split the track string into chunks (or 'segments')
    # by the time we're done, each chunk should contain only one 'instruction'
    # we can then iterate over the instructions (keeping track of state) and create the track

    # setup some utilities for parsing
    timingRegex = r'^([0-9]+.?)' # I use this timing regex twice, so I decided to make it a variable
    # this function allows us to parse out string tokens and leave finished chords alone (chords are immediately turned into arrays)
    # It's not really parsing out because they're still in the segments. fixing this would make parsing easier (using tokens)
    def parseOut(regex):
      return list(chain.from_iterable([[segment] if not isinstance(segment,str) else re.split(regex, segment) for segment in segments]))
    # this function is used to throw parsing errors
    def parseError(instruc,fileIdx,fileName):
      raise Exception("Parse error on "+str(instruc)+"\n instruction#: "+str(fileIdx)+"\n in file: "+fileName)
    # parse out instrument changes
    segments = parseOut(r'(i[0-9]+)')
    # parse out global volume changes
    segments = parseOut(r'(l[0-9]+)')
    # parse out rests
    segments = parseOut(r'(r)')
    # parse out octave changes
    segments = parseOut(r'(o[-+]?[0-9]+)')
    # parse out tempo changes
    segments = parseOut(r'(t[0-9]+)')
    # parse out volume changes (0-100 scale)
    segments = parseOut(r'(v[0-9]+)')
    # parse out inversions
    segments = parseOut(r'(n[0-9]+)')
    # replace flats with sharps
    for flatFrom,flatTo in flatReplace:
      segments = [segment.replace(flatFrom,flatTo) for segment in segments]
    # parse out the chords
    for chordInstruc,chord in chordOrderedMap:
      # parse out this chord
      segments = parseOut("("+chordInstruc+")")
      # turn this chord directly into an array (preventing sub-strings from being parsed)
      segments = [chord if instruc == chordInstruc else instruc for instruc in segments]
    # parse timing changes
    segments = parseOut(timingRegex)
    # remove whitespace
    segments = parseOut(r'[, \n]')
    # remove any residue (empty instructions)
    instructions = [instrc for instrc in segments if instrc is not None]
    instructions = [instrc for instrc in segments if instrc not in ['']]
    # all instructions should be parsed. now iterate over the instructions and create the track
    for fileIdx,instruc in enumerate(instructions):
      try:
        if not isinstance(instruc,str):
          # if we're not a string, we're a chord. add it
          chord = instruc
          # make sure to add the octave and set the note length and volume correctly
          track.append(instrumentFunc(chord+octave*12,l=speed,v=volume/100))
        elif re.match(timingRegex, instruc):
          # change the length of notes
          base = re.split(r'([0-9]+)', instruc)[1]
          speed = 1/int(base)
          if instruc[-1] == '.':
            # if the last character is a dot, make it a dotted note
            speed *= 1.5
        elif instruc[0] == 'i':
          # change the instrument being played
          instrumentFunc = instrumentMap[int(instruc[1:])]
        elif instruc[0] == 'n':
          # this modifies the last chord
          track[-1].chord = inv(track[-1].chord,int(instruc[1:])-1)
        elif instruc[0] == 'r':
          # insert a rest (at the current note length)
          track.append(rest(l=speed))
        elif instruc[0] == 'o':
          # change the octave
          if instruc[1] == '-' or instruc[1] == '+':
            # relative changes
            octave += int(instruc[1:])
          else:
            # absolute change
            octave = int(instruc[1:])-4
        elif instruc[0] == 't':
          # change the BPM (tempo)
          # this is global, so it will change the whole song (uses last one)
          tempo = int(instruc[1:])
        elif instruc[0] == 'v':
          # change the volume
          volume = int(instruc[1:])
        elif instruc[0] == 'l':
          # change the global volume
          globalVol = int(instruc[1:])
        else:
          parseError(instruc,fileIdx,fileName)
      except Exception as e:
        # catch any error here
        print(e)
        parseError(instruc,fileIdx,fileName)
    tracks.append(track)

  # create an array of samples (song) 
  song = np.array([])
  for chords in tracks:
    # iterate through reach track to find samples
    fs = 44100.0 # frames per second (frames=samples)
    noteDur = 60/tempo*4 # duration (in seconds) of a whole note
    noteF = fs*noteDur # f is for frames (# frames for a whole note)
    # find the total number of samples in this track
    totalF = 0
    for chord in chords:
      totalF += chord.length*noteF

    # find the samples for this track
    trackSamples = np.zeros(int(np.floor(totalF)),dtype=np.float)
    frequency = 440.0 # frequency of root chord
    counter = 0 # used to count the samples already collected
    for chord in chords:
      # iterate through each chord in the track
      # mark and increment the counter
      firstSampleIdx = int(np.floor(counter))
      counter += chord.length*noteF # keep this as a float for precision
      lastSampleIdx = int(np.floor(counter))
      # get the number of samples in this chord
      thisChordF = int(lastSampleIdx - firstSampleIdx)
      # number of tones is used for mixing notes (and not clipping)
      numberTones = len(chord.chord)
      for ti,t in enumerate(sorted(chord.chord)):
        # interate through each note in the chord
        # sorted so that strumming works for guitar
        # get the note's frequency
        f = frequency*2**(t/12)/2
        # check which instrument it is
        if chord.instr == 1: # organ
          # FM synthesize
          t = np.arange(thisChordF)
          # these parameters sound alright
          l = 1.01
          a = 40
          w0 = 2*np.pi*f/fs # original frequency
          w1 = w0*l # modified frequency
          secondWav = np.sin(t*w1)
          trackSamples[firstSampleIdx:lastSampleIdx] += np.sin(w0*(t+a*secondWav))**5/numberTones
        else:
          # mimic strum by delaying higher notes
          delay=ti*800
          # Karplus-Strong
          t = np.linspace(0,1,int(fs/f))
          noiseAmount = .8 # how much white noise
          N = int(fs/f) # period of the sample
          noiseTable = np.random.rand(N)*2-1
          waveTable = noiseTable*noiseAmount + (np.sin(2*np.pi*t)**1)*(1-noiseAmount)
          Y = np.concatenate((waveTable,np.zeros(thisChordF-delay)))
          for idx in range(0,thisChordF-delay):
            pluckIdx = idx + N
            Y[pluckIdx] = (waveTable[idx] if idx<N else 0) + 0.5*(Y[idx]+Y[idx+1])
          # add this pluck to the track samples
          #   the last bit helps bring out chords, if it's set to '1', it's disabled. Test it out by setting to 1.01 or something
          trackSamples[firstSampleIdx+delay:lastSampleIdx] += Y[N:]/numberTones*(numberTones**1)
      # do FIR filtering (low-pass)
      for i in range(0,chord.lowPass):
        n = trackSamples[firstSampleIdx:lastSampleIdx]
        n_1 = np.concatenate(([0],trackSamples[firstSampleIdx:lastSampleIdx-1]))
        trackSamples[firstSampleIdx:lastSampleIdx] = (n+n_1)/2
      # do enveloping
      segLengths = np.floor(chord.env*thisChordF).astype(np.int)
      segVols = chord.envVols # assume we start and end at zero
      prevSegLength = firstSampleIdx
      for segi,segLength in enumerate(segLengths):
        lower = prevSegLength 
        upper = lower + segLength
        prevSegLength = upper
        if segi == 0: # attack
          trackSamples[lower:upper] = trackSamples[lower:upper]*np.linspace(0,segVols[0],segLength)
        elif segi == 1: # decay
          trackSamples[lower:upper] = trackSamples[lower:upper]*np.linspace(segVols[0],segVols[1],segLength)
        elif segi == 2: # sustain
          trackSamples[lower:upper] = trackSamples[lower:upper]*segVols[1]
        elif segi == 3: # release
          trackSamples[lower:upper] = trackSamples[lower:upper]*np.linspace(segVols[1],0,segLength)
    # add this track to the song
    maxLength = max(trackSamples.shape[0], song.shape[0])
    newSong = np.zeros(maxLength)
    newSong[0:song.shape[0]] += song
    newSong[0:trackSamples.shape[0]] += trackSamples/len(tracks)
    song = newSong

# normalize the volume
maxVol = song[np.argmax(np.abs(song))]
if maxVol != 0: # this would mean the song is empty
  song = song/maxVol

# apply the global volume
song = song*(globalVol/100)

# write out the wav file
wavfile.write(wavName, int(fs), song)
