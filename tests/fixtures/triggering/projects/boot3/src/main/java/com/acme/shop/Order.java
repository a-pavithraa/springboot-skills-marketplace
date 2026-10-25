package com.acme.shop;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "orders")
public class Order {
    @Id @GeneratedValue Long id;
    String customerName;
    @OneToMany(mappedBy = "order") List<OrderLine> lines = new ArrayList<>();

    public Long getId() { return id; }
    public String getCustomerName() { return customerName; }
    public List<OrderLine> getLines() { return lines; }
    public BigDecimal total() {
        return lines.stream().map(OrderLine::amount).reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
