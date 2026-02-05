# The Tower Game Automation Bot
> This scripts is made by gemini and some human power

This repository contains a Python-based automation bot for "The Tower Game". The bot uses computer vision techniques to identify and interact with game elements, enabling automated gameplay.
## Features
- Automated detection and interaction with game elements using OpenCV.
- Configurable settings for targeting specific game objects.
- Background click functionality to interact with the game window without bringing it to the foreground.
## Requirements
- Python 3.x
- OpenCV
- NumPy
- pywin32
- Pillow
## Installation
1. Clone the repository:
   ```bash
   git clone
   ```
2. Install the required packages:
   ```bash
    pip install -r requirements.txt
    ```
## Usage
1. Replace `templates` folder's images as your feature

2. Update `processed_templates` feature content using `test.py`
   * 2-1 uncomment `pr.precompute_templates('templates/float-dm-template.png', angle_step=1)` in `test.py`
   * 2-2 comment all the line under you uncomment
   * 2-3 run `test.py` to generate processed templates

3. Run the main script:
   ```bash
   python main.py
   ```
## Configuration
- Modify the `target_objects` list in `main.py` to specify which game elements to target.
- Adjust the `enable_restart` flag to enable or disable automatic restart button detection.
## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.