# Test Coverage for Order Service

## Background

The team at Meridian Commerce has an `OrderService` that calculates order discounts and exposes secured REST endpoints for managing orders. A code review flagged that the existing test suite tests the happy path only and uses Spring's built-in test login helpers instead of going through the app's own role-mapping code.

The service stub is under `inputs/src/main/java/com/example/orders/`. It includes:

- `OrderService.java` — the domain service with a `calculateDiscount` method and Javadoc that specifies the discount rules precisely
- `OrderController.java` — REST endpoints for listing and creating orders, secured with `@PreAuthorize`
- `SecurityConfig.java` — a `JwtAuthenticationConverter` bean that reads a `"roles"` JWT claim and maps it to `ROLE_` authorities
- `Order.java` — the domain model

Your task is to write tests that cover the discount rules from the Javadoc contract and the route access rules for the secured endpoints.

## What to produce

Write the test files in `src/test/java/com/example/orders/`. Specifically:

1. **`OrderServicePropertyTest.java`** — property-based tests for `calculateDiscount`. Cover the discount rules as stated in the Javadoc, using generated inputs. Include boundary values explicitly in the generated data.

2. **`OrderRouteAccessTest.java`** — route access tests that check which personas may call `GET /orders` and `POST /orders`. Sign in through the app's own role-mapping code rather than handing the test a pre-built role. Include a Personas helper class (or inline helper) in the same file or as a companion file `Personas.java` in the same package.

3. **`test-report.md`** — a written report that lists:
   - each test added, its behavior, and the level (unit / integration / property)
   - how each test was shown to fail (which line was broken and what the test output was)
   - any tests that fail on the current code and the contract clause they rely on
   - contract clauses from the Javadoc that remain untested

Place all output files under `src/test/java/com/example/orders/` and `test-report.md` in the working directory root.
