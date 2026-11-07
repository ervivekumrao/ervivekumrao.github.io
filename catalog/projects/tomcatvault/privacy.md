# Privacy Policy for Tomcat Vault

*Last updated: June 10, 2026*

Tomcat Vault ("the Tool") is an enterprise-grade cryptographic credential manager and DataSource factory for Apache Tomcat connection pools.

## 1. No Telemetry or Data Collection
The Tool does not collect, store, or transmit any encrypted or decrypted data. All encryption and decryption operations are performed locally on your machine or within your server's JVM environment.

## 2. Encryption Keys & Secrets
Master keys, HSM/KeyStore credentials, and cloud vault tokens remain strictly within your infrastructure boundaries. The Tool adheres to zero-leak logging principles and masks credentials in JMX MBeans.

## 3. Server Integration
When integrated into Tomcat, the Tool only decrypts attributes defined in local configuration files (`context.xml`, `server.xml`) during DataSource initialization and dynamic reload events.

## 4. Contact Us
For any questions, please contact `manuscriptcode@gmail.com`.
