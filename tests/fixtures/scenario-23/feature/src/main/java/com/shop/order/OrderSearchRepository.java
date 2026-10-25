package com.shop.order;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import java.math.BigDecimal; import java.util.List;
@Repository
public class OrderSearchRepository {
  private final JdbcClient jdbc;
  OrderSearchRepository(JdbcClient jdbc){this.jdbc=jdbc;}
  public record Row(Long id, BigDecimal total) {}
  public List<Row> search(Long customerId, String sort) {
    return jdbc.sql("select id, total from orders where customer_id = :cid order by " + sort + " limit 50")
        .param("cid", customerId).query(Row.class).list();
  }
}
