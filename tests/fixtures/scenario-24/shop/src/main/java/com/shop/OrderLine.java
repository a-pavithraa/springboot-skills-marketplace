package com.shop;
import jakarta.persistence.*; import java.math.BigDecimal;
@Entity @Table(name = "order_lines")
public class OrderLine {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
  @ManyToOne(fetch = FetchType.LAZY) private PurchaseOrder order;
  @ManyToOne(cascade = CascadeType.ALL) private Product product;
  private int quantity;
  private BigDecimal unitPrice;
  protected OrderLine() {}
  public OrderLine(PurchaseOrder order, Product product, int quantity, BigDecimal unitPrice) {
    this.order = order; this.product = product; this.quantity = quantity; this.unitPrice = unitPrice; }
  public Long getId() { return id; }
  public PurchaseOrder getOrder() { return order; }
  public Product getProduct() { return product; }
  public int getQuantity() { return quantity; }
  public BigDecimal getUnitPrice() { return unitPrice; }
}
