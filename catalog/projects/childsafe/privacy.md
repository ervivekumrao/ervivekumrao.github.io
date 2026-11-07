# Privacy Policy for Child Safe

*Last updated: June 10, 2026*

Child Safe ("the App", package `control.child.device`) values the safety and privacy of families above all else. This policy details how data is handled, stored, and protected.

## 1. Ethical Commitment & Purpose of Data Collection
Child Safe is designed exclusively for parents and legal guardians to protect and guide their children's digital activities. The App collects data solely for parental monitoring, device governance, and child safety.
- **Zero Third-Party Data Sales:** Personal data is never monetized, rented, or shared with third-party ad networks or data brokers.
- **No Surreptitious Surveillance:** The App is intended strictly for child safety management and must not be used for unauthorized tracking of adults.

## 2. Data Types Collected & Usage
- **Real-Time Location & Route History:** Collected to allow authorized parents to locate their child in real time and view movement traces. Location data is securely transmitted over TLS 1.3 encrypted pipes.
- **App Usage & System Status Logs:** Used to enforce screen time quotas, monitor app usage intervals, and report device battery/connectivity status to the parent dashboard.
- **Device Identifiers:** Device ID and model details are used solely to pair the child device with the parent account.

## 3. Permissions & System Protections
To provide enterprise-grade protection, Child Safe utilizes specialized Android system permissions:
- **Device Owner (Device Policy Manager API):** Enables tamper-proof security, anti-uninstallation safeguards, and hardware lockdowns (camera/mic/USB restrictions).
- **Location (Fine & Background Location):** Enables live GPS position updates and periodic route tracking.
- **Accessibility Service:** Used to monitor active app foreground transitions, enforce weekly screen time limits, and lock non-whitelisted apps during Kiosk Mode.

## 4. Data Encryption & Architecture
- **Transport Security:** All communication between the child's device, Firebase Realtime Database, and the parent dashboard uses TLS 1.3 encryption.
- **Local Storage:** Policy rules and cached data on the device are stored securely in local Room Database instances.
- **Data Erasure on Demand:** Parents can request complete data erasure or delete their account and associated device logs at any time directly from the app or by contacting support.

## 5. Google Play Policy Compliance
Child Safe strictly complies with Google Play's `child_monitoring` metadata specifications and Families Policy requirements.

## 6. Contact Us
If you have questions regarding this Privacy Policy or data security practices, please contact us at:
`manuscriptcode@gmail.com`
