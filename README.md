## Firmware (Arduino) — Dual-Slot Smart Tool Shelf Logic

# This Arduino firmware controls a two-slot smart tool shelf using:

* 2× RC522 RFID readers (MFRC522 library, shared SPI bus)

2× Load Cells + HX711 (weight sensing)

2× Red/Green LED pairs (status indication)

The goal is to provide a simple local rule:

Green LED = Authorized AND Tool Present (weight above threshold)
Otherwise, the LED stays Red.

Key Features

Two independent slots (System 1 / System 2)

Each slot has its own RFID reader, HX711 scale, and LED pair.

RFID authorization with UID whitelist

Slot 1 accepts two allowed UIDs.

Slot 2 accepts one allowed UID.

Authorization toggle

When a valid card is detected, the slot’s authorization state toggles:

toggle = !toggle

Weight threshold detection

The firmware reads weight using scale.get_units() and compares it against a threshold.

Clear LED status

Green only when (authorized == true) && (weight > threshold)

Otherwise Red

Serial debug output

Prints slot authorization, weight, and LED state once per second.

Hardware Pin Mapping

Slot 1

HX711: DOUT = D3, SCK = D2

LEDs: RED = D8, GREEN = D9

RFID SS (SDA): D5

Slot 2

HX711: DOUT = D4, SCK = D13

LEDs: RED = D10, GREEN = D11

RFID SS (SDA): D6

Shared

RFID RST: D7

SPI bus: shared by both RC522 modules (different SS pins)

RFID Authorization Rules (UID Whitelist)

Slot 1: accepts either UID_1 or UID_2

Slot 2: accepts UID_2_SINGLE only

If a scanned UID is not on the whitelist, it is ignored and does not change the authorization state.

LED Logic

For each slot:

Read RFID card (if present)

If UID is valid → toggle authorization state

Read weight from HX711

Determine weightOK = (weight > 0.5)

Set LED:

Green if toggle && weightOK

Red otherwise

Serial Output

Every 1 second, the firmware prints:

Authorization state: TRUE / FALSE

Current weight (absolute value)

Current LED state: Green / Red

This helps verify RFID scans and weight detection during testing.

Notes

The weight threshold is set to 0.5 (see TARGET_WEIGHT_G).
Adjust this value depending on your sensor calibration and real tool weight.

The calibration factor is currently set to 100000.0f (CALIBRATION_FACTOR).
You may need to tune it for your specific load cell setup.
