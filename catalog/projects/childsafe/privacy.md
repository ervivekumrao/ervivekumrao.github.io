# Privacy Policy for Child Safe

*Last updated: November 7, 2026*

Child Safe ("the App", package `control.child.device`) values the safety and privacy of families above all else. This policy details how minimal data is collected, encrypted, and handled.

## 1. Ethical Commitment & Minimal Data Philosophy
Child Safe is designed exclusively for parents and legal guardians to protect and guide their children's digital safety. 
- **Minimal Data Collection:** The App collects only the minimal data strictly required to synchronize policies, location updates, and safety logs between the parent and child device.
- **Immediate Sync Payload Cleanup:** Temporary relay payload buffers transmitted to sync queues are automatically deleted once delivered to the parent device.
- **Zero Third-Party Data Sales:** Personal data is never monetized, rented, analyzed for marketing, or shared with third-party ad networks or data brokers.
- **No Surreptitious Surveillance:** The App is intended strictly for authorized parental governance of minor children.

## 2. Encryption & Data Confidentiality
- **End-to-End Encryption:** All data transmitted between the child device, intermediate relay servers, and the parent dashboard is strongly encrypted.
- **Zero Server Access Reading:** Data is encrypted in transit and at rest such that no third party—including server administrators, hosting providers, or database operators—can read, decrypt, or inspect location coordinates, family communications, or device logs.

## 3. Location Data & Real-Time Tracking Privacy
- **Minimal Location Processing:** Location data (GPS/network location) is accessed solely to fulfill real-time location requests and scheduled route history snapshots configured by the parent.
- **Encrypted Transmission:** Location coordinates are encrypted end-to-end before leaving the child device.
- **Last Location Retention for Parent Dashboard:** To ensure seamless monitoring upon subsequent logins, the most recent (last known) location snapshot collected by the parent is retained securely in encrypted storage. This allows the parent to view the child's last recorded position immediately when logging back into the parent app.
- **Purged Staging Queues:** Intermediate transport payload queues are purged once received and synced.

## 4. Other Data Types Collected & Temporary Usage
- **App Usage & System Status:** Collected solely to enforce weekly usage quotas, display real-time app metrics to parents, and report battery/connectivity status.
- **Call Logs, SMS & Contact Audits:** Processed exclusively for parental safety oversight and encrypted end-to-end.
- **Device Identifiers:** Anonymous cryptographic tokens used solely to pair the child device with the authorized parent account.

## 5. Permissions & System Protections
Child Safe utilizes specialized Android system permissions to enforce safety:
- **Device Owner (Device Policy Manager API):** Enables tamper-proof security, anti-uninstallation safeguards, and system restrictions.
- **Location (Fine & Background Location):** Used exclusively for live GPS location updates, last known location display, and parent-configured route snapshots.
- **Accessibility Service:** Used to monitor active app transitions, enforce weekly screen time limits, and lock non-whitelisted apps in Kiosk Mode.

## 6. Data Retention & On-Demand Erasure
Parents maintain total control over their accounts and data:
- **Last Location Snapshot:** Only the latest location record is retained to display on the parent dashboard during subsequent logins.
- **Local Device Wipes:** Local cached data stored in the app's Room Database can be wiped instantly by parents directly from the app.
- **Account & Data Deletion Requests:** Parents can request complete account deletion, removal of paired device profiles, and total erasure of all associated data at any time by contacting support.

## 7. Contact Us & Data Deletion Requests
If you have any questions regarding this Privacy Policy or wish to request **account deletion or complete data erasure**, please contact us at:

📧 **Email:** `manuscriptcode@gmail.com`
