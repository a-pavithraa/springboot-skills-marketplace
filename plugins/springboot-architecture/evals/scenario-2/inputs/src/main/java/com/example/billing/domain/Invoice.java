package com.example.billing.domain;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import java.math.BigDecimal;

@Entity
public class Invoice {

    @Id
    @GeneratedValue
    private Long id;

    private String customer;

    private BigDecimal amount;

    protected Invoice() {
    }

    public Invoice(String customer, BigDecimal amount) {
        this.customer = customer;
        this.amount = amount;
    }

    public Long getId() {
        return id;
    }

    public String getCustomer() {
        return customer;
    }

    public BigDecimal getAmount() {
        return amount;
    }
}
