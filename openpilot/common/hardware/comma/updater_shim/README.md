# updater_shim

The AGNOS `updater` binary next to this directory is a standalone zipapp that
comma builds only at release time. The current bundle still does
`import serial` (pyserial) in its bundled `lpa.py`, but AGNOS 19.5+ no longer
ships pyserial, so the updater crashes on boot with
`ModuleNotFoundError: No module named 'serial'` whenever an AGNOS update is
required (see commaai/openpilot#38623).

`launch_chffrplus.sh` puts this directory on `PYTHONPATH` when it runs the
updater. `serial.py` here is a symlink to `openpilot/common/serial.py`, comma's
own pyserial replacement, so the bundled `lpa.py` imports it instead.

Drop this directory and the `PYTHONPATH` line once upstream ships a rebuilt
updater bundle.
