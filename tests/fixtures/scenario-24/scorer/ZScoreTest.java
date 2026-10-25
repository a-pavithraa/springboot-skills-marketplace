package com.shop;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;
import javax.sql.DataSource;
import java.lang.reflect.*;
import java.math.BigDecimal;
import java.sql.Connection;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;

/** Hidden scorer: 200 orders, counts JDBC statements per request. */
@SpringBootTest @AutoConfigureMockMvc
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class ZScoreTest {
  static final AtomicInteger STATEMENTS = new AtomicInteger();

  @TestConfiguration static class Counting {
    @Bean static BeanPostProcessor countingDataSource() {
      return new BeanPostProcessor() {
        @Override public Object postProcessAfterInitialization(Object bean, String name) {
          if (!(bean instanceof DataSource ds)) return bean;
          return Proxy.newProxyInstance(DataSource.class.getClassLoader(), new Class<?>[]{DataSource.class}, (p, m, a) -> {
            Object r = invoke(ds, m, a);
            if (r instanceof Connection c) {
              return Proxy.newProxyInstance(Connection.class.getClassLoader(), new Class<?>[]{Connection.class}, (p2, m2, a2) -> {
                if (m2.getName().equals("prepareStatement") || m2.getName().equals("prepareCall") || m2.getName().equals("createStatement")) STATEMENTS.incrementAndGet();
                return invoke(c, m2, a2);
              });
            }
            return r;
          });
        }
      };
    }
    static Object invoke(Object t, Method m, Object[] a) throws Throwable {
      try { return m.invoke(t, a); } catch (InvocationTargetException e) { throw e.getCause(); }
    }
  }

  @Autowired MockMvc mvc; @Autowired JdbcTemplate jdbc;
  static final Map<String, String> SCORE = new LinkedHashMap<>();

  @BeforeEach void seed() {
    jdbc.update("delete from order_lines"); jdbc.update("delete from orders");
    jdbc.update("delete from products"); jdbc.update("delete from customers");
    List<Object[]> c = new ArrayList<>(), p = new ArrayList<>(), o = new ArrayList<>(), l = new ArrayList<>();
    for (int i = 1; i <= 50; i++) c.add(new Object[]{1000 + i, "Customer " + i});
    for (int i = 1; i <= 30; i++) p.add(new Object[]{1000 + i, "Product " + i, new BigDecimal(i * 10 + ".00")});
    p.add(new Object[]{2000, "Only on line 9999", new BigDecimal("5.00")});
    long line = 1;
    for (int i = 1; i <= 200; i++) {
      o.add(new Object[]{1000 + i, 1000 + (i % 50) + 1});
      for (int k = 0; k < 3; k++) l.add(new Object[]{line++, 1000 + i, 1000 + ((i + k) % 30) + 1, k + 1, new BigDecimal("10.00")});
    }
    l.add(new Object[]{9999, 1001, 2000, 1, new BigDecimal("5.00")});
    jdbc.batchUpdate("insert into customers(id, name) values (?, ?)", c);
    jdbc.batchUpdate("insert into products(id, name, price) values (?, ?, ?)", p);
    jdbc.batchUpdate("insert into orders(id, customer_id, placed_at) values (?, ?, now())", o);
    jdbc.batchUpdate("insert into order_lines(id, order_id, product_id, quantity, unit_price) values (?, ?, ?, ?, ?)", l);
  }

  int run(org.springframework.test.web.servlet.RequestBuilder rb, StringBuilder body) throws Exception {
    STATEMENTS.set(0);
    var res = mvc.perform(rb).andReturn().getResponse();
    if (body != null) body.append(res.getContentAsString());
    SCORE.put("status:" + rb.toString().hashCode(), "" + res.getStatus());
    return STATEMENTS.get();
  }

  @Test @Order(1) void list() throws Exception {
    StringBuilder b = new StringBuilder();
    int n = run(get("/api/orders"), b);
    Object doc = JsonPath.read(b.toString(), "$");
    List<?> items = doc instanceof List<?> li ? li : (List<?>) JsonPath.read(b.toString(), "$.content");
    Map<?, ?> first = (Map<?, ?>) items.get(0);
    SCORE.put("P1 list statements", "" + n);
    SCORE.put("P2 list items returned", "" + items.size());
    SCORE.put("list first item correct", "" + (first.get("customerName") != null && first.get("lineCount") != null && first.get("total") != null));
  }

  @Test @Order(2) void detail() throws Exception {
    StringBuilder b = new StringBuilder();
    int n = run(get("/api/orders/1001"), b);
    int lines = JsonPath.<List<?>>read(b.toString(), "$.lines").size();
    SCORE.put("P3 get one statements", "" + n);
    SCORE.put("get one correct (4 lines)", "" + (lines == 4));
  }

  @Test @Order(3) void removeLine() throws Exception {
    STATEMENTS.set(0);
    int status = mvc.perform(delete("/api/orders/1001/lines/9999")).andReturn().getResponse().getStatus();
    Integer products = jdbc.queryForObject("select count(*) from products where id = 2000", Integer.class);
    Integer line = jdbc.queryForObject("select count(*) from order_lines where id = 9999", Integer.class);
    SCORE.put("P4 remove line: status/line gone/product kept", status + "/" + (line == 0) + "/" + (products == 1));
  }

  @Test @Order(4) void reprice() throws Exception {
    int n = run(post("/api/products/reprice").param("percent", "10"), null);
    BigDecimal p = jdbc.queryForObject("select price from products where id = 1030", BigDecimal.class);
    SCORE.put("P5 reprice statements", "" + n);
    SCORE.put("reprice correct (300 -> 330)", "" + (p.compareTo(new BigDecimal("330.00")) == 0));
  }

  @AfterAll static void print() {
    SCORE.forEach((k, v) -> { if (!k.startsWith("status:")) System.out.println("SCORE| " + k + " = " + v); });
  }
}
