# Privacy Policy for JitForge

*Last updated: June 10, 2026*

JitForge ("the Engine") is a high-performance in-memory runtime compilation, JIT execution, and bytecode synthesis engine.

## 1. No Data Collection
The Engine does not collect, store, or transmit any user source code or compiled bytecode to external third-party tracking services. All compilation and execution tasks are performed in-memory within your JVM or containerized microservice instance.

## 2. Sandboxed Execution Safety
JitForge incorporates lexical AST security rules and execution timeouts via `SandboxedExecutor` to proactively reject forbidden APIs and runaway execution.

## 3. Tiered Bytecode Storage
When persistence tiers (Redis, local disk volumes, PostgreSQL) are configured, bytecode is stored strictly within the developer's designated infrastructure boundaries.

## 4. Contact Us
For any questions, please contact `manuscriptcode@gmail.com`.
