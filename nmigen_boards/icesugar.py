import os
import subprocess
import platform

from nmigen.build import *
from nmigen.vendor.lattice_ice40 import *
from .resources import *

if platform.system() == "Windows":
    # Libraries required to identify removable drives
    # Provided as part of pywin32
    import win32api
    import win32con
    import win32file

if platform.system() == "Linux":
    # Library required to identify and find the mount point of removable drives
    # Provided as part of blkinfo
    import blkinfo

__all__ = ["ICESugarPlatform"]

def _findDriveMountPoint():
    if platform.system() == "Darwin":
        icedrives = ["/Volumes/iCELink"]
    elif platform.system() == "Windows":
        drives = [i for i in win32api.GetLogicalDriveStrings().split('\x00') if i]
        rdrives = [d for d in drives if win32file.GetDriveType(d) == win32con.DRIVE_REMOVABLE]
        icedrives = [d for d in rdrives if win32api.GetVolumeInformation(d)[0] == "iCELink"]
    elif platform.system() == "Linux":
        icedrives  = [x['mountpoint'] for x in blkinfo.BlkDiskInfo().get_disks() if x['label'] == "iCELink" and x['model'] == "MBED VFS"]
    else:
        raise NotImplementedError("Support for programming on this platform not yet added")

    assert len(icedrives) > 0, "Unable to identify an iCELink - is board connected via the USB C programming connector?"
    assert len(icedrives) < 2, "More than one iCELink connected - remove extras and try again"
    return icedrives[0]

class ICESugarPlatform(LatticeICE40Platform):
    device      = "iCE40UP5K"
    package     = "SG48"
    default_clk = "clk12"
    resources   = [
        Resource("clk12", 0, Pins("35", dir="i"),
                 Clock(12e6), Attrs(GLOBAL=True, IO_STANDARD="SB_LVCMOS")),

        *LEDResources(pins="40 41 39", invert=True, attrs=Attrs(IO_STANDARD="SB_LVCMOS")),
        # Semantic aliases
        Resource("led_r", 0, PinsN("40", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS")),
        Resource("led_g", 0, PinsN("41", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS")),
        Resource("led_b", 0, PinsN("39", dir="o"), Attrs(IO_STANDARD="SB_LVCMOS")),

        *SwitchResources(
            pins="18 19 20 21",
            attrs=Attrs(IO_STANDARD="SB_LVCMOS")
        ),

        UARTResource(0,
            rx="4", tx="6",
            attrs=Attrs(IO_STANDARD="SB_LVTTL", PULLUP=1)
        ),

        *SPIFlashResources(0,
            cs="16", clk="15", mosi="14", miso="17", wp="12", hold="13",
            attrs=Attrs(IO_STANDARD="SB_LVCMOS")
        ),

        Resource("usb", 0,
            Subsignal("d_p",    Pins("10", dir="io")),
            Subsignal("d_n",    Pins("9", dir="io")),
            Subsignal("pullup", Pins("11", dir="o")),
            Attrs(IO_STANDARD="SB_LVCMOS")
        ),
    ]
    connectors = [
        Connector("pmod", 0, "10  6  3 48 - -  9  4  2 47 - -"), # PMOD1 - IO pins shared by USB
        Connector("pmod", 1, "46 44 42 37 - - 45 43 38 36 - -"), # PMOD2
        Connector("pmod", 2, "34 31 27 25 - - 32 28 26 23 - -"), # PMOD3
        Connector("pmod", 3, "21 20 19 18 - -  -  -  -  - - -"), # PMOD4 - IO pins used for switches via jumpers
    ]

    def toolchain_program(self, products, name):
        with products.extract("{}.bin".format(name)) as bitstream_filename:
            subprocess.check_call(["cp", bitstream_filename, _findDriveMountPoint()])


if __name__ == "__main__":
    from .test.blinky import *
    p = ICESugarPlatform()
    p.build(Blinky(), do_program=True)
