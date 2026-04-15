# Tkinter GUI

This contains directory contains the code for the GUI of the program

## Requirements

Install the required packages:

I can put the libraries in the repo later, but I have not used uv and am using Conda.

Used libraries:

* `tkinter`
* `opencv-python`
* `Pillow`

## Running

Run the scripts from the root directory:

This is the detection backend that is modified to broadcast the webcam and overlay to the GUI
```bash
python cv_backend/detector.py
```

Next, run the GUI itself. The detector.py script **MUST** be running before the overlay will work or it will throw an error.
```bash
python overlay.py
```

A window will open showing the **live webcam stream**.

## Notes

None for now. Let the discord know of any issues.