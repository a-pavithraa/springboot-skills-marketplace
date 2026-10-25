package com.shop.order;
import jakarta.persistence.*; import java.math.BigDecimal; import java.time.Instant; import java.util.*;
@Entity @Table(name="orders")
public class Order {
  @Id @GeneratedValue Long id;
  Long customerId; Instant placedAt; BigDecimal total;
  @OneToMany(mappedBy="order", fetch=FetchType.LAZY) List<OrderLine> lines = new ArrayList<>();
  public Long getId(){return id;} public Long getCustomerId(){return customerId;} public Instant getPlacedAt(){return placedAt;}
  public BigDecimal getTotal(){return total;} public List<OrderLine> getLines(){return lines;}
}
