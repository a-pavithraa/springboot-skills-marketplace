package com.shop;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal; import java.util.*;
@Service
public class OrderService {
  public record OrderSummary(Long id, String customerName, long lineCount, BigDecimal total) {}
  public record LineView(Long id, String productName, int quantity, BigDecimal unitPrice) {}
  public record OrderDetail(Long id, String customerName, List<LineView> lines) {}

  private final OrderRepository orders; private final OrderLineRepository lines;
  OrderService(OrderRepository orders, OrderLineRepository lines) { this.orders = orders; this.lines = lines; }

  /** Feeds the orders screen, which shows 20 orders at a time. Production has thousands of orders. */
  @Transactional(readOnly = true)
  public List<OrderSummary> list() {
    List<OrderSummary> result = new ArrayList<>();
    for (PurchaseOrder o : orders.findAll()) {
      long count = lines.countByOrderId(o.getId());
      BigDecimal total = lines.findByOrderId(o.getId()).stream()
          .map(l -> l.getUnitPrice().multiply(BigDecimal.valueOf(l.getQuantity())))
          .reduce(BigDecimal.ZERO, BigDecimal::add);
      result.add(new OrderSummary(o.getId(), o.getCustomer().getName(), count, total));
    }
    return result;
  }

  @Transactional(readOnly = true)
  public OrderDetail get(Long id) {
    PurchaseOrder o = orders.findById(id).orElseThrow(NoSuchElementException::new);
    List<LineView> views = o.getLines().stream()
        .map(l -> new LineView(l.getId(), l.getProduct().getName(), l.getQuantity(), l.getUnitPrice())).toList();
    return new OrderDetail(o.getId(), o.getCustomer().getName(), views);
  }

  @Transactional
  public void removeLine(Long orderId, Long lineId) {
    PurchaseOrder o = orders.findById(orderId).orElseThrow(NoSuchElementException::new);
    boolean removed = o.getLines().removeIf(l -> l.getId().equals(lineId));
    if (!removed) throw new NoSuchElementException();
  }
}
