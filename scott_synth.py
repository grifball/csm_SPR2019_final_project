import sys
import numpy as np
from scipy.io import wavfile
import wave, struct, math, random
from random import random
from numpy import c_

'''
Scott Griffy's Computers Sound and Music project
Read the README for more information
'''

#chords = [[0,4,7],[9,12,4]]
#chords = [[0],[1]]
#chords = [[0],[2],[4],[5],[7],[9],[11],[12]]
#chords = np.array([[0],[2],[4],[5],[7],[9],[11],[12]])+2
#major3 = np.array([0,4]*12)
#chords = major3+np.array([[0],[2],[4],[5],[7],[9],[11],[12]])
#chords = np.array([[0],[2],[4],[5],[7],[9],[11],[12]])-12*1-2
#chords = [[0,4,7,11],[0,4,7,11],[0,4,7,11]]
class Chord():
  # This class represents multiple notes played at the same length
  def __init__(self, chord, instr, length, vol=1, env=np.array([.1,.1,.6,.2])):
    self.chord = chord
    self.instr = instr
    self.length = length
    self.env = env
    self.envVols = np.array([1,.75])*vol

# invert an array the represents a chord
def inv(chord, times=1):
  for time in range(0,times):
    chord = np.append(chord[1:],chord[0]+12)
  return chord

# create a chord from notes which uses the guitar instrument
def guitar(chord,l=1/4,v=1):
  if len(chord.shape)>1 and chord.shape[1]>0:
    chords = []
    for ch in chord:
      chords.append(guitar(ch, l, v))
    return chords
  return Chord(chord, 0, l, env=np.array([0, 0, 1, 0]))

# create a chord from notes which uses the organ instrument
def organ(chord,l=1/4,v=1):
  if len(chord.shape)>1 and chord.shape[1]>0:
    chords = []
    for ch in chord:
      chords.append(organ(ch, l, v))
    return chords
  return Chord(chord, 1, l, vol=v)

# create some symbols for chords
CM7 = np.array([0,4,7,11])
C7 = np.array([0,4,7,10])
C6 = np.array([0,4,7,9])
Cm7 = np.array([0,3,7,10])
AM7 = CM7 - 3
Am7 = Cm7 - 3
Dm7 = Cm7 + 2
GM7 = AM7 - 2 + 12
G7 = C7 - 2 + 12

# setup first track
chords1 = [organ(Dm7,1/2, v=1), organ(inv(G7)-12,1/4, v=1), organ(CM7,1/2, v=1), organ(C6,1/2, v=1)]

# setup second track
#chords2 = [guitar(Dm7,1/2), guitar(inv(G7)-12,1/4), guitar(CM7,1/4), guitar(C6,1/2)]
F = np.array([5])
Gs = np.array([8])
C = np.array([0])
G = np.array([7])
guitarChords = np.array([Dm7,C+5,C+8,C+11,C+12,C+7,inv(C6)])
chords2 = []
for chord in guitarChords:
  chords2.append(guitar(chord))
chords2 = np.array(chords2)

# combine tracks
tracks = [chords1, chords2]

# create an array of samples (song) 
song = np.array([])
for chords in tracks:
  # iterate through reach track to find samples
  fs = 44100.0 # frames per second (frames=samples)
  noteDur = 3 # duration (in seconds) of a whole note
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
      if chord.instr == 1: # organe
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
        # add this pluck to the track samples (last bit helps bring out chords)
        trackSamples[firstSampleIdx+delay:lastSampleIdx] += Y[N:]/numberTones*(numberTones**1.001)
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
  # add this to the song
  maxLength = max(trackSamples.shape[0], song.shape[0])
  newSong = np.zeros(maxLength)
  newSong[0:song.shape[0]] += song
  newSong[0:trackSamples.shape[0]] += trackSamples/len(tracks)
  song = newSong

# write out the wav file
wavfile.write("sound.wav", int(fs), song)
print("Written to ./sound.wav")
