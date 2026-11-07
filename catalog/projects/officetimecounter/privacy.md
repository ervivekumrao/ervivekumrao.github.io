# Privacy Policy for Office Time Counter

*Last updated: June 17, 2026*

Welcome to **Office Time Counter**. We take your privacy seriously. This document outlines how we handle your data, specifically focusing on sensitive permissions like Location and Notifications.

## 1. Location Data Disclosure
Office Time Counter requires access to your device's location to provide its core functionality of automated attendance tracking:
- **Geofence Monitoring:** The app accesses Background Location (`ACCESS_BACKGROUND_LOCATION`), Fine Location (`ACCESS_FINE_LOCATION`), and Coarse Location (`ACCESS_COARSE_LOCATION`) to monitor when you enter or exit specific office coordinates.
- **Automatic Logging:** When a Geofence transition is detected (Entering or Leaving), the app automatically records the timestamp to create your "In Time" and "Out Time" logs.
- **Data Storage:** All location processing happens locally on your device via the Android Geofencing API. We do **not** transmit your real-time location or movement history to external servers.

## 2. Notification Access
The app uses a Notification Listener Service to identify "Check-in" or "Check-out" messages sent by specific organization-approved companion apps:
- We only read notifications from specific configured package names. Personal messages, emails, or other private notifications are completely ignored.

## 3. Data Storage & Security
Your attendance logs (In/Out times) are stored in a secure local Room database on your device.

## 4. Your Controls
- You can revoke Location or Notification permissions at any time through Android System Settings.
- You can delete your entire attendance history from within app settings.
- Geofencing is optional; you can use the app for manual logging without granting location permissions.

## 5. Contact Us
If you have any questions regarding this privacy policy or our data practices, please contact us at:
`manuscriptcode@gmail.com`
