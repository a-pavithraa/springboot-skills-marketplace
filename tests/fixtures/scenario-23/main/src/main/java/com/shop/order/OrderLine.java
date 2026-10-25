package com.shop.order;
import jakarta.persistence.*; import java.math.BigDecimal;
@Entity @Table(name="order_lines")
public class OrderLine {
  @Id @GeneratedValue Long id;
  @ManyToOne(fetch=FetchType.LAZY) Order order;
  String sku; int quantity; BigDecimal price;
  public String getSku(){return sku;} public int getQuantity(){return quantity;} public BigDecimal getPrice(){return price;}
}
