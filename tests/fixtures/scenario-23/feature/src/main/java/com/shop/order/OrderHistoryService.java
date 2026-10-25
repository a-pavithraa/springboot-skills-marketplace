package com.shop.order;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal; import java.util.*;
@Service
public class OrderHistoryService {
  private final OrderRepository orders;
  OrderHistoryService(OrderRepository orders){this.orders=orders;}

  public record HistoryRow(Long orderId, int items, BigDecimal total) {}

  @Transactional(readOnly=true)
  public List<HistoryRow> history(Long customerId) {
    List<HistoryRow> rows = new ArrayList<>();
    for (Order o : orders.findByCustomerId(customerId)) {
      int items = o.getLines().stream().mapToInt(OrderLine::getQuantity).sum();
      rows.add(new HistoryRow(o.getId(), items, o.getTotal()));
    }
    return rows;
  }

  @Transactional(readOnly=true)
  public BigDecimal revenueReport() {
    return orders.findAll().stream().map(Order::getTotal).reduce(BigDecimal.ZERO, BigDecimal::add);
  }
}
