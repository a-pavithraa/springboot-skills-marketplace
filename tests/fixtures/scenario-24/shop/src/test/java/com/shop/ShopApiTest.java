package com.shop;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.hamcrest.Matchers.*;

/** The HTTP contract of the shop API. */
@SpringBootTest @AutoConfigureMockMvc
class ShopApiTest {
  @Autowired MockMvc mvc; @Autowired JdbcTemplate jdbc;

  @BeforeEach void seed() {
    jdbc.update("delete from order_lines"); jdbc.update("delete from orders");
    jdbc.update("delete from products"); jdbc.update("delete from customers");
    jdbc.update("insert into customers(id, name) values (1, 'Asha')");
    jdbc.update("insert into products(id, name, price) values (1, 'Pen', 10.00), (2, 'Book', 250.00)");
    jdbc.update("insert into orders(id, customer_id, placed_at) values (1, 1, now())");
    jdbc.update("insert into order_lines(id, order_id, product_id, quantity, unit_price) values (1, 1, 1, 3, 10.00), (2, 1, 2, 1, 250.00)");
  }

  @Test void listsOrderSummaries() throws Exception {
    mvc.perform(get("/api/orders")).andExpect(status().isOk())
        .andExpect(jsonPath("$[0].id").value(1))
        .andExpect(jsonPath("$[0].customerName").value("Asha"))
        .andExpect(jsonPath("$[0].lineCount").value(2))
        .andExpect(jsonPath("$[0].total").value(280.0));
  }

  @Test void showsOrderDetail() throws Exception {
    mvc.perform(get("/api/orders/1")).andExpect(status().isOk())
        .andExpect(jsonPath("$.customerName").value("Asha"))
        .andExpect(jsonPath("$.lines", hasSize(2)))
        .andExpect(jsonPath("$.lines[*].productName", containsInAnyOrder("Pen", "Book")));
  }

  @Test void unknownOrderIs404() throws Exception {
    mvc.perform(get("/api/orders/99")).andExpect(status().isNotFound());
  }

  @Test void removesALine() throws Exception {
    mvc.perform(delete("/api/orders/1/lines/1")).andExpect(status().isNoContent());
    mvc.perform(get("/api/orders/1")).andExpect(jsonPath("$.lines", hasSize(1)));
  }

  @Test void repricesAllProducts() throws Exception {
    mvc.perform(post("/api/products/reprice").param("percent", "10")).andExpect(status().isNoContent());
    mvc.perform(get("/api/orders/1")).andExpect(status().isOk());
    org.assertj.core.api.Assertions.assertThat(jdbc.queryForObject("select price from products where id = 2", java.math.BigDecimal.class))
        .isEqualByComparingTo("275.00");
  }
}
