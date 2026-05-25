# Bluetooth Meter Integration Guide

How to connect any Bluetooth glucose meter to the T1D Companion backend.

## Architecture

```
Meter (any brand)
    ↓ Bluetooth
Phone App (iOS/Android/Flutter)
    ↓
POST /api/v1/glucose/bluetooth  ← Our backend (ready now)
    ↓
PostgreSQL
```

Our backend is meter-agnostic. It doesn't care what brand sent the reading. The phone handles the Bluetooth pairing; we just store the data.

## Endpoint

### POST /api/v1/glucose/bluetooth

Log a reading from any Bluetooth-paired glucose meter.

**Request:**

```json
{
  "glucose_value": 5.8,
  "glucose_units": "mmol/L",
  "timestamp": "2026-05-25T12:30:00Z",
  "reading_type": "fingerstick",
  "source": "bluetooth_meter",
  "source_device_id": "caresens-n-premier-bt-serial123"
}
```

Supported `source` values (for analytics tracking):

| Source | Meter |
|--------|-------|
| `bluetooth_meter` | Generic / unknown |
| `accuchek` | Accu-Chek Guide, Guide Me |
| `contour` | Contour Next One, Next EZ |
| `onetouch` | OneTouch Verio Flex, Verio IQ |
| `caresens` | CareSens N Premier BT, Dual |
| `glukomen` | GlucoMen Areo |

**Response:**

```json
{
  "id": 12345,
  "glucose_value": 104.5,
  "glucose_units": "mg/dL",
  "reading_type": "fingerstick",
  "source": "bluetooth_meter",
  "created_at": "2026-05-25T12:30:05Z"
}
```

> Note: values are stored as mg/dL internally. mmol/L is converted automatically.

## Phone-Side Requirements

To make this seamless, the mobile app needs to:

1. **Scan for nearby Bluetooth meters** (standard BLE device scan)
2. **Pair with the meter** (follow the meter's pairing procedure)
3. **Listen for readings** (meters broadcast when a test strip is used)
4. **Send reading to our API** (POST the data immediately)

### Per-Meter Notes

| Meter | BLE Service UUID | Data Format | Known Working |
|-------|-----------------|-------------|---------------|
| Accu-Chek Guide | Vendor-specific | Custom BLE characteristic | ⚠️ Needs testing |
| Contour Next One | Vendor-specific | Uses MCTP transport | ⚠️ Needs testing |
| OneTouch Verio Flex | Vendor-specific | Custom BLE characteristic | ⚠️ Needs testing |
| CareSens N Premier BT | Vendor-specific | Custom BLE characteristic | ⚠️ Needs testing |

Each meter uses a proprietary BLE protocol. There is no universal standard for BG meter data. The phone app will need a per-meter adapter that knows how to pair, read, and parse each meter's data format.

### Reference: Existing Open-Source Projects

These projects have already done the reverse-engineering for many meters:

- **[xDrip+](https://github.com/NightscoutFoundation/xDrip)** (Android) — Supports Accu-Chek, Contour, OneTouch, CareSens, and more. GPL licensed.
- **[Shuggah](https://github.com/creepymonster/GlucoseDirect)** (iOS) — Supports many meters via BLE.
- **[Diabox](https://www.diabox.app/)** — Supports CareSens, Contour, Accu-Chek.

Using xDrip+ as a reference, pairing with a CareSens meter looks like:

```kotlin
// Pseudocode for Android BLE connection
val meter = bluetoothAdapter.getRemoteDevice(address)
meter.connectGatt(context, false, object : BluetoothGattCallback() {
    override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
        val reading = parseCaresensReading(characteristic.value)
        api.postGlucoseReading(reading.value, "mmol/L", source = "caresens")
    }
})
```

## Testing Without a Meter

Use the manual endpoint to simulate readings:

```bash
# Terminal: log a reading as if it came from Bluetooth
python scripts/log_reading.py 5.8 mmol/L
```

Or via curl:

```bash
curl -X POST http://localhost:8000/api/v1/glucose/bluetooth \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"glucose_value": 5.8, "glucose_units": "mmol/L", "timestamp": "2026-05-25T12:30:00Z", "reading_type": "fingerstick", "source": "caresens"}'
```

## Companion App Awareness

Once readings are flowing, the companion automatically:

- Displays "Manual logging mode" for users without CGM data
- Shows confidence: LOW for sparse data, improving over time
- Provides educational advice based on logged readings
- Detects patterns once enough data accumulates (~2 weeks of regular testing)