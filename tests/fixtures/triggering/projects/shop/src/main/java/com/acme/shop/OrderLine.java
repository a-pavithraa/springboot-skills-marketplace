package com.acme.shop;

import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
public class OrderLine {
    @Id @GeneratedValue Long id;
    @ManyToOne Order order;
    String sku;
    int quantity;
    BigDecimal unitPrice;

    BigDecimal amount() { return unitPrice.multiply(BigDecimal.valueOf(quantity)); }
}
