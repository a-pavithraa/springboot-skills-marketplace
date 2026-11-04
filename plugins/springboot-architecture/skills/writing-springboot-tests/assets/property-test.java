package {{PACKAGE}}.orders.domain;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Property tests for domain logic: each test states a rule that holds for every input, then checks it on generated
 * inputs. Plain JUnit, no library: jqwik tells AI agents in its output to ignore its results, and its engine targets
 * JUnit Platform 1.x while Boot 4 manages 6.x.
 *
 * Properties, written down before the code (from the requirement, not from the code):
 * - invariant: after any sequence of added lines, the order total is the sum of quantity x unit price, never negative
 * - round trip: an order number printed and parsed back is the same order number
 * - idempotence: cancelling a cancelled order changes nothing
 */
class OrderPropertiesTest {

    // A fixed seed makes every run see the same inputs, so a failure reproduces. Change it to explore new inputs;
    // keep the failing case as an example test once it's fixed.
    static final long SEED = 20261104L;
    static final int CASES = 500;

    record Line(String product, int quantity, BigDecimal unitPrice) {}

    // Random values rarely hit boundaries, so the generator mixes them in on purpose: 1, the largest quantity the
    // rules allow, zero-priced lines, prices with the most decimals the currency allows.
    static List<Line> lines(SplittableRandom random) {
        int count = random.nextInt(0, 20);
        List<Line> lines = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            int quantity = switch (random.nextInt(4)) {
                case 0 -> 1;
                case 1 -> Order.MAX_QUANTITY;
                default -> random.nextInt(1, Order.MAX_QUANTITY + 1);
            };
            BigDecimal price = random.nextInt(10) == 0
                    ? BigDecimal.ZERO
                    : BigDecimal.valueOf(random.nextLong(1, 1_000_000), 2);
            lines.add(new Line("P-" + random.nextInt(50), quantity, price));
        }
        return lines;
    }

    static Stream<List<Line>> orders() {
        var random = new SplittableRandom(SEED);
        return Stream.generate(() -> lines(random)).limit(CASES);
    }

    static Stream<OrderNumber> orderNumbers() {
        var random = new SplittableRandom(SEED);
        return Stream.generate(() -> new OrderNumber(random.nextInt(2000, 2100), random.nextLong(1, 10_000_000)))
                .limit(CASES);
    }

    // Surefire names a failing case by its index only, so each assertion carries its input with as(...). There is no
    // shrinking: if the failing input is large, cut it down by hand to the smallest one that still fails.
    @ParameterizedTest
    @MethodSource("orders")
    void totalIsTheSumOfItsLines(List<Line> lines) {
        Order order = Order.open();
        BigDecimal expected = BigDecimal.ZERO;
        for (Line line : lines) {
            order.addLine(line.product(), line.quantity(), line.unitPrice());
            expected = expected.add(line.unitPrice().multiply(BigDecimal.valueOf(line.quantity())));

            assertThat(order.total()).as("total after %s", line).isEqualByComparingTo(expected);
            assertThat(order.total()).as("total after %s", line).isNotNegative();
        }
    }

    @ParameterizedTest
    @MethodSource("orderNumbers")
    void anOrderNumberSurvivesPrintingAndParsing(OrderNumber number) {
        assertThat(OrderNumber.parse(number.toString())).as("parsing %s", number).isEqualTo(number);
    }

    @ParameterizedTest
    @MethodSource("orders")
    void cancellingTwiceIsTheSameAsCancellingOnce(List<Line> lines) {
        Order order = Order.open();
        for (Line line : lines) {
            order.addLine(line.product(), line.quantity(), line.unitPrice());
        }
        order.cancel();
        OrderStatus status = order.status();
        BigDecimal total = order.total();

        order.cancel();

        assertThat(order.status()).as("status after cancelling twice, lines %s", lines).isEqualTo(status);
        assertThat(order.total()).as("total after cancelling twice, lines %s", lines).isEqualByComparingTo(total);
    }
}

// The expected value comes from the rule, computed the plain way (sum of quantity x price), never by calling the
// code under test. Before calling these done, run PIT on Order and OrderNumber: a mutant that survives every property
// is a rule nobody stated. PIT setup: code-reviewer/references/testing/boot4-test-toolkit.md.
