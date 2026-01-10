# Microscope Control System – Raman 2D Scanning App

A **PyQt6-based desktop application** for controlling a microscope setup and performing **2D Raman mapping scans**.  
The application integrates camera imaging, motorized stage control, and Raman spectrometer acquisition into a single interactive GUI.

This repository currently includes **fully functional dummy devices**, allowing the entire workflow to be tested without physical hardware.

---

## Features

- **Camera View & ROI Selection**
  - Live image capture;
  - Interactive region-of-interest (ROI) selection;
  - Export of raw and annotated camera images;

- **Raman 2D Scanning**
  - Grid-based 2D scanning over selected ROI;
  - Configurable step sizes (X/Y);
  - Integrated Raman intensity heatmap;

- **Live Visualization**
  - Real-time heatmap updates during scanning;
  - Spectrum viewer with interactive Raman range selection;
  - Click heatmap pixels to inspect individual spectra;

- **Project Save & Load**
  - Custom `.raman2dscan` project format
  - Stores:
    - Scan metadata;
    - Spectral data (CSV);
    - Heatmap grid;
    - Heatmap image;
    - Camera overview & raw images;

- **Simulation Mode**
  - Dummy camera, spectrometer, and motor controller;
  - For UI testing and development without hardware;

---

## Getting Started

1. Install Dependencies

Recommended Python version: Python 3.10+

```pip install -r requirements.txt```

2. Run the Application

```python scanning_app/main.py```

## Usage Workflow

1. Connect Devices

    - Select Dummy Camera, Dummy Spectrometer, and Dummy Motor Controller

2. Capture Image

    - Acquire a camera image

3. Draw ROI

    - Click & drag on the camera image

4. Configure Scan

    - Set step size and Raman integration range

5. Start Scan

    - Watch live heatmap & spectra update

6. Save Project

    - Export results as a .raman2dscan file

7. Reload Anytime

    - Open saved scans in viewer mode
