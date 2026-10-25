package com.acme.shop;

import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class OrderService {
    private final OrderRepository orders;

    OrderService(OrderRepository orders) { this.orders = orders; }

    public List<Order> list() { return orders.findAll(); }

    public Order get(Long id) { return orders.findById(id).orElseThrow(); }
}
