package com.shop;
import jakarta.persistence.*; import java.math.BigDecimal;
@Entity @Table(name = "products")
public class Product {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
  private String name;
  private BigDecimal price;
  protected Product() {}
  public Product(String name, BigDecimal price) { this.name = name; this.price = price; }
  public Long getId() { return id; }
  public String getName() { return name; }
  public BigDecimal getPrice() { return price; }
  public void setPrice(BigDecimal price) { this.price = price; }
}
