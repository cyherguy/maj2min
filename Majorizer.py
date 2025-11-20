import mido
import os
from collections import defaultdict
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox

root = tk.Tk()
root.withdraw()

finput = filedialog.askopenfilename(
    title="Select your MIDI file",
    filetypes=[("MIDI files", "*.mid *.midi")])

baseName = os.path.splitext(os.path.basename(finput))[0]
defaultName = f"{baseName.lower()}_MAJORISED.mid"

foutput = filedialog.asksaveasfilename(
    title="Save your MIDI file as",
    initialfile=defaultName,
    defaultextension=".mid",
    filetypes=[("MIDI files", "*.mid *.midi")])

notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
majorProfile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
minorProfile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

print("""-----------------------------------------------------------------------------
Copyright (c) 2025 David Willis
All rights reserved.

This script may not be copied, modified, or distributed without permission.
-----------------------------------------------------------------------------\n""")

def analyseKey(mid: mido.MidiFile) -> tuple[int, str]:
    cpitchc = defaultdict(int)
    totalDuration = 0
    for track in mid.tracks:
        active = {}
        currentTime = 0
        for msg in track:
            currentTime += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                active[msg.note] = currentTime
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                if msg.note in active:
                    duration = currentTime - active[msg.note]
                    pitchClass = msg.note % 12
                    cpitchc[pitchClass] += duration
                    totalDuration += duration
                    del active[msg.note]
    
    if totalDuration == 0: return 0, "minor"
    pitchClassHistogram = [cpitchc[i] / totalDuration for i in range(12)]

    bestScore, detectedKey = -1, (0, "minor")
    for i in range(12):
        for mode, profile in [("major", majorProfile), ("minor", minorProfile)]:
            keyProfile = np.roll(profile, i)
            correlation = np.dot(pitchClassHistogram, keyProfile)
            if correlation > bestScore:
                bestScore, detectedKey = correlation, (i, mode)
    return detectedKey

def convertRelative(mid: mido.MidiFile) -> mido.MidiFile:
    newMIDI = mido.MidiFile(type=mid.type, ticks_per_beat=mid.ticks_per_beat)
    for track in mid.tracks:
        newTrack = mido.MidiTrack()
        for msg in track:
            newMsg = msg.copy()
            if newMsg.type in ("note_on", "note_off"):
                newMsg.note = min(127, newMsg.note + 3)
            newTrack.append(newMsg)
        newMIDI.tracks.append(newTrack)
    return newMIDI

def convertParallel(mid: mido.MidiFile, tonicpc: int) -> mido.MidiFile:
    m3 = (tonicpc + 3) % 12
    m6 = (tonicpc + 8) % 12
    m7 = (tonicpc + 10) % 12
    transposed = {m3, m6, m7}
    
    newMIDI = mido.MidiFile(type=mid.type, ticks_per_beat=mid.ticks_per_beat)
    for track in mid.tracks:
        newTrack = mido.MidiTrack()
        for msg in track:
            if msg.type in ["note_on", "note_off"]:
                pitchClass = msg.note % 12
                if pitchClass in transposed:
                    newNote = min(127, msg.note + 1)
                    newTrack.append(msg.copy(note=newNote))
                else:
                    newTrack.append(msg)
            else:
                newTrack.append(msg)
        newMIDI.tracks.append(newTrack)
    return newMIDI

def main():
    if not finput or not finput.lower().endswith(('.mid', '.midi')):
        print(f'You must select a valid .mid or .midi file.')
        return
        
    try:
        midOriginal = mido.MidiFile(finput)
        print(f'Input file: "{finput}"')
    except Exception as e:
        print(f"Could not read MIDI file. Details: {e}")
        return

    print("\nAnalyzing key...")
    tonicpc, mode = analyseKey(midOriginal)
    tonicName = notes[tonicpc]
    print(f"Key found: {tonicName} {mode.capitalize()}")
    
    if mode != "minor":
        print("\nThis song's key is NOT minor. Your file did not save, please try again.")
        return

    choice = ""
    while choice not in ["1", "2"]:
        print("\nPlease choose a conversion method:")
        print(f"  1: Relative major (convert {tonicName} Minor -> {notes[(tonicpc + 3) % 12]} Major)")
        print(f"  2: Parallel major (convert {tonicName} Minor -> {tonicName} Major)")
        choice = input("Enter your choice (1 or 2): ").strip()

    midMajor = None
    newKeyName = ""

    if choice == "1":
        print("\nConverting to relative major...")
        midMajor = convertRelative(midOriginal)
        newKeyName = f"{notes[(tonicpc + 3) % 12]} Major"
    elif choice == "2":
        print("\nConverting to parallel major...")
        midMajor = convertParallel(midOriginal, tonicpc)
        newKeyName = f"{tonicName} Major"

    if midMajor:
        try:
            midMajor.save(foutput)
            print("-" * 30)
            print("Conversion successful! Thanks for trying this program.")
            print(f"   Original key: {tonicName} Minor")
            print(f"   New key:      {newKeyName}")
            print(f'Saved output to: "{foutput}"')
        except Exception as e:
            print(f"Could not save the new MIDI file. Details: {e}")

if __name__ == "__main__":
    main()