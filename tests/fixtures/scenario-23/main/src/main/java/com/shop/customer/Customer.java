package com.shop.customer;
import jakarta.persistence.*;
@Entity @Table(name="customers")
public class Customer {
  @Id @GeneratedValue Long id;
  String email;
  String name;
  String passwordHash;
  public Long getId(){return id;} public String getEmail(){return email;} public String getName(){return name;}
  public String getPasswordHash(){return passwordHash;}
}
