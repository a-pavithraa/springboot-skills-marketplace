package com.shop;
import jakarta.persistence.*; import java.time.Instant; import java.util.*;
@Entity @Table(name = "orders")
public class PurchaseOrder {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
  @ManyToOne(fetch = FetchType.LAZY) private Customer customer;
  private Instant placedAt;
  @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
  private List<OrderLine> lines = new ArrayList<>();
  protected PurchaseOrder() {}
  public PurchaseOrder(Customer customer, Instant placedAt) { this.customer = customer; this.placedAt = placedAt; }
  public Long getId() { return id; }
  public Customer getCustomer() { return customer; }
  public Instant getPlacedAt() { return placedAt; }
  public List<OrderLine> getLines() { return lines; }
}
