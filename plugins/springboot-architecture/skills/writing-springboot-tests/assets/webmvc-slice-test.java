package {{PACKAGE}}.orders.web;

import {{PACKAGE}}.orders.domain.InsufficientStockException;
import {{PACKAGE}}.orders.domain.Order;
import {{PACKAGE}}.orders.domain.OrderService;
import {{PACKAGE}}.orders.domain.OrderStatus;
import {{PACKAGE}}.orders.domain.PlaceOrder;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

import java.math.BigDecimal;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * Web slice: loads only OrderController, the MVC machinery and @RestControllerAdvice handlers.
 * It tests what the service test can't see: mapping, validation, status codes, JSON shape, error bodies.
 *
 * Expected statuses come from the API contract. The creating-springboot-projects GlobalExceptionHandler
 * answers invalid input with 400 and a ProblemDetail listing the errors, and broken business rules
 * (DomainException) with 422: assert what YOUR handler documents, and if the code disagrees with the
 * contract, report it rather than changing the test.
 */
@WebMvcTest(OrderController.class)
class OrderControllerTest {

    @Autowired
    MockMvcTester mvc;

    @MockitoBean
    OrderService orders;   // the layer below the controller: mocked, because its rules have their own test

    @Test
    void placingAnOrderAnswersCreatedWithTheOrderAndItsLocation() {
        given(orders.place(any(PlaceOrder.class))).willReturn(new Order(
                "O-1", "P-1", 3, new BigDecimal("37.50"), OrderStatus.PLACED, Instant.parse("2026-10-21T10:00:00Z")));

        var result = mvc.post().uri("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"productCode": "P-1", "quantity": 3}
                        """);

        assertThat(result)
                .hasStatus(HttpStatus.CREATED)
                .hasHeader("Location", "http://localhost/api/orders/O-1");
        assertThat(result).bodyJson().isLenientlyEqualTo("""
                {"id": "O-1", "productCode": "P-1", "quantity": 3, "total": 37.50, "status": "PLACED"}
                """);
    }

    @Test
    void rejectsAMissingProductCodeWithoutCallingTheService() {
        var result = mvc.post().uri("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"quantity": 3}
                        """);

        assertThat(result).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(result).bodyJson().extractingPath("$.errors").asArray().isNotEmpty();
        verifyNoInteractions(orders);   // invalid input must never reach the business layer
    }

    @Test
    void answersInsufficientStockAsAProblemDetail() {
        given(orders.place(any(PlaceOrder.class))).willThrow(new InsufficientStockException("P-1", 3, 1));

        var result = mvc.post().uri("/api/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"productCode": "P-1", "quantity": 3}
                        """);

        assertThat(result).hasStatus(HttpStatus.UNPROCESSABLE_ENTITY);
        assertThat(result).bodyJson().extractingPath("$.detail").asString().contains("P-1");
    }

    @Test
    void answersNotFoundForAnUnknownOrder() {
        given(orders.find("O-404")).willReturn(java.util.Optional.empty());

        assertThat(mvc.get().uri("/api/orders/O-404"))
                .hasStatus(HttpStatus.NOT_FOUND);
    }
}

// With Spring Security on the classpath, also test who may call it:
//   mvc.post().uri(...).with(user("ann").roles("CUSTOMER")).with(csrf())   → allowed
//   the same request without .with(user(...))                             → 401
// (static imports from org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors)
