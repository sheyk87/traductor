"""Main entrypoint for video translator: supports both GUI and CLI."""

import sys

if __name__ == "__main__":
    # If called with no arguments or explicitly with --gui, launch the Tkinter GUI
    if len(sys.argv) == 1 or "--gui" in sys.argv:
        if "--gui" in sys.argv:
            sys.argv.remove("--gui")
        from gui import launch_gui
        launch_gui()
    else:
        from cli import main
        main()
