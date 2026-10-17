"""GBA code no C compiles to is recognized as hand-written assembly, so agents aren't sent to it."""

from decompnet.rom.gba import hand_written


def test_bios_call_veneers_and_libgcc_routines_are_hand_written():
    assert hand_written(bytes.fromhex("0adf7047")) == "_swi_0A"              # swi #10; bx lr
    assert hand_written(bytes.fromhex("06df081c70470000")) == "_swi_06"      # swi #6; adds r0, r1, #0; bx lr
    assert hand_written(bytes.fromhex("f7460000")) == "_libgcc_thumb"        # mov pc, lr (no interworking)
    assert hand_written(bytes.fromhex("1847c046")) == "_call_via_r3"         # bx r3; nop


def test_compiled_code_is_not():
    assert hand_written(bytes.fromhex("7047")) is None                      # bx lr: an empty C function
    assert hand_written(bytes.fromhex("00b5 0120 02bc 0847".replace(" ", ""))) is None  # push {lr}; ...; bx r1
    assert hand_written(bytes.fromhex("0adf0120704700")[:6] + b"\x00\x00\x00\x00") is None  # a swi in a longer body
