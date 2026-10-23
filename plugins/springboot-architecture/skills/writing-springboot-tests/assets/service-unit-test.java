package {{PACKAGE}}.orders.domain;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.context.ApplicationEventPublisher;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.AdditionalAnswers.returnsFirstArg;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * Unit test for a service with business rules: plain JUnit + Mockito, no Spring context.
 *
 * Intent, written down before the tests (from the requirement, not from the code):
 * - placing an order charges unit price x quantity, stores it as PLACED, and announces OrderPlaced
 * - an order for more than the available stock is rejected, and nothing is reserved, stored, or charged
 * - a quantity below 1 is rejected
 * - the order records when it was placed
 */
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock
    InventoryClient inventory;           // another service or module: a boundary we don't run here

    @Mock
    PaymentGateway payments;             // external and paid: mocked

    @Mock
    OrderRepository orders;              // its queries have their own @DataJpaTest; here we check WHAT is saved

    @Mock
    ApplicationEventPublisher events;

    // A fixed clock makes time assertable. Never assert "close to now".
    final Clock clock = Clock.fixed(Instant.parse("2026-10-21T10:00:00Z"), ZoneOffset.UTC);

    OrderService service;                // the subject: always the real class

    @BeforeEach
    void setUp() {
        service = new OrderService(inventory, payments, orders, events, clock);
    }

    @Test
    void chargesUnitPriceTimesQuantityAndStoresThePlacedOrder() {
        // 3 x 12.50 = 37.50, worked out by hand. Never compute it with the service's own formula.
        given(inventory.available("P-1")).willReturn(10);
        given(inventory.unitPrice("P-1")).willReturn(new BigDecimal("12.50"));
        given(orders.save(any(Order.class))).will(returnsFirstArg());

        Order order = service.place(new PlaceOrder("P-1", 3));

        var saved = ArgumentCaptor.forClass(Order.class);
        verify(orders).save(saved.capture());
        assertThat(saved.getValue().total()).isEqualByComparingTo("37.50");
        assertThat(saved.getValue().status()).isEqualTo(OrderStatus.PLACED);
        verify(payments).charge(order.id(), new BigDecimal("37.50"));   // the charge IS the behaviour: verify its content
        verify(inventory).reserve("P-1", 3);
    }

    @Test
    void announcesThePlacedOrderToOtherModules() {
        given(inventory.available("P-1")).willReturn(10);
        given(inventory.unitPrice("P-1")).willReturn(new BigDecimal("12.50"));
        given(orders.save(any(Order.class))).will(returnsFirstArg());

        Order order = service.place(new PlaceOrder("P-1", 2));

        verify(events).publishEvent(new OrderPlaced(order.id(), "P-1", 2, new BigDecimal("25.00")));
    }

    @Test
    void acceptsAnOrderForExactlyTheAvailableStock() {
        // Boundary: stock == quantity. A `<` vs `<=` slip in the code fails here.
        given(inventory.available("P-1")).willReturn(3);
        given(inventory.unitPrice("P-1")).willReturn(new BigDecimal("1.00"));
        given(orders.save(any(Order.class))).will(returnsFirstArg());

        Order order = service.place(new PlaceOrder("P-1", 3));

        assertThat(order.status()).isEqualTo(OrderStatus.PLACED);
    }

    @Test
    void rejectsAnOrderForMoreThanTheAvailableStockAndChangesNothing() {
        given(inventory.available("P-1")).willReturn(3);

        assertThatThrownBy(() -> service.place(new PlaceOrder("P-1", 4)))
                .isInstanceOf(InsufficientStockException.class)
                .hasMessageContaining("P-1");
        verifyNoInteractions(payments, orders, events);   // the side effects that must NOT happen
    }

    @ParameterizedTest(name = "quantity {0} is rejected")
    @ValueSource(ints = {0, -1})
    void rejectsQuantitiesBelowOne(int quantity) {
        assertThatThrownBy(() -> service.place(new PlaceOrder("P-1", quantity)))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("quantity");
        verifyNoInteractions(payments, orders);
    }

    @Test
    void recordsWhenTheOrderWasPlaced() {
        given(inventory.available("P-1")).willReturn(1);
        given(inventory.unitPrice("P-1")).willReturn(new BigDecimal("1.00"));
        given(orders.save(any(Order.class))).will(returnsFirstArg());

        Order order = service.place(new PlaceOrder("P-1", 1));

        assertThat(order.placedAt()).isEqualTo(Instant.parse("2026-10-21T10:00:00Z"));
    }
}

// Before calling these done: run PIT on OrderService, or break `available < quantity` (try `<=`), drop the
// `payments.charge` call, and remove the quantity check, one at a time. Each must turn at least one test red.
// PIT setup: code-reviewer/references/testing/boot4-test-toolkit.md.
