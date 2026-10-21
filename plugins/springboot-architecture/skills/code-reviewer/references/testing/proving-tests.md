# Proving Tests Can Fail

A test earns its place by failing when the behaviour it guards breaks. Agents rarely check this, and the research on generated tests shows why it matters: many generated assertions pass on the buggy code too.

**Use PIT first** for any class with unit tests. In a trial on an `OrderService` (39 mutants), PIT took 6 seconds. A hand-run sabotage loop over the same class, through Maven and a container per run, did not finish in 10 minutes. Break code by hand only where PIT is not set up, or for tests that need Spring or containers.

## 1. Sabotage by hand (no PIT, or Spring/container tests)

For each new test:

1. Find the line of production code the test is about.
2. Break it on purpose, in the smallest way that changes the behaviour:
   - flip a comparison (`<` to `<=`, `>` to `>=`)
   - return early, or return an empty or default value
   - remove a call with a side effect (`save`, `publish`, `charge`)
   - change a constant or a boundary by one
3. Run only that test class (`./mvnw -q test -Dtest=OrderServiceTest`), never the whole suite per break. **It must fail, and for the right reason**: an assertion failure on the behaviour, not a compile error or a `NullPointerException` in setup.
4. Restore the code and run it again: green.

If the test stays green, it does not guard that line. Strengthen the assertion, or say that the test covers something else.

Report it like this:

```markdown
- `OrderServiceTest#rejectsOrderWhenStockIsInsufficient`: changed `stock < quantity` to `stock <= quantity` → failed (expected InsufficientStockException, none thrown). Restored.
```

Never leave a sabotage in place. Check `git diff` on production code before finishing.

## 2. Mutation testing with PIT (the default for classes with logic)

PIT makes many small sabotages automatically (mutants) and reports which ones no test catches (survivors). Meta uses the same idea to keep only generated tests that catch real faults.

Run it on the classes you just tested, not the whole project. Start with unit and slice tests: PIT runs the tests once per mutant, so tests that start containers make it very slow.

### Maven setup

Add the plugin from `../../../writing-springboot-tests/assets/pitest-plugin.xml` (versions checked on Maven Central in October 2026: `pitest-maven` 1.30.1, `pitest-junit5-plugin` 1.2.3). Then run it for one class:

```bash
./mvnw test-compile org.pitest:pitest-maven:mutationCoverage \
  -DtargetClasses=com.example.orders.domain.OrderService \
  -DtargetTests='com.example.orders.domain.*Test'
```

The report is in `target/pit-reports/index.html`.

### Reading survivors

| Survivor | Usually means | Do |
|----------|---------------|----|
| Changed conditional boundary | No test sits on the boundary value | Add the `limit` and `limit + 1` cases |
| Negated conditional | A branch is never asserted | Add a test for the other branch |
| Removed void method call | A side effect is never checked | Assert the stored row, or the call with `verify` |
| Replaced return value with null / 0 / empty | The return value is never asserted exactly | Assert the exact value |
| Mutant in logging or `toString` | Doesn't matter | Leave it; say so |

Some mutants cannot change behaviour (equivalent mutants). Name them, and move on. Don't chase 100%; chase survivors in the logic the change is about.

**PIT and Spring tests:** a cached application context builds each bean once, so mutants in constructors and `@PostConstruct` code survive however good the tests are. Survivors like "Removed assignment to member variable" in a Spring-context test are this artifact, not a gap. One more reason to test logic in plain unit tests.

### Gradle

Use the `info.solidsoft.pitest` plugin with `junit5PluginVersion` set; the parameters have the same names.

## When to skip PIT

- Pure wiring, configuration, or DTO classes
- Tests that need Docker, unless the run is in CI with time for it
- A change that only touches tests. Run the sabotage check instead
