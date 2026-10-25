package com.shop;
import jakarta.persistence.*;
@Entity @Table(name = "customers")
public class Customer {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
  private String name;
  protected Customer() {}
  public Customer(String name) { this.name = name; }
  public Long getId() { return id; }
  public String getName() { return name; }
}
